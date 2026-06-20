import time
import threading
import os
import tempfile
import wave
import numpy as np
import pyaudio
import queue
from typing import Optional
from collections import deque
from pii_mask import PIIMask
from transcriber import LocalTranscriber
from diarization import SpeakerDiarizer
from whitelist import Whitelist
from audit_log import AuditLog
from echo_canceller import AcousticEchoCanceller

SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
SAMPLE_WIDTH = 2
CHUNK = 1024
WINDOW_SECONDS = 3
HOP_SECONDS = 1.5
BUFFER_SECONDS = 10
OUTPUT_CHUNK_MS = 20

CHUNK_OUTPUT = int(SAMPLE_RATE * OUTPUT_CHUNK_MS / 1000)


class AudioRedactor:
    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate

    def _beep(self, num_samples: int, beep_freq: float = 880.0):
        t = np.arange(num_samples, dtype=np.float64) / self.sample_rate
        tone = np.sin(2 * np.pi * beep_freq * t) + 0.5 * np.sin(2 * np.pi * beep_freq * 1.5 * t)
        tone /= np.max(np.abs(tone))
        fade = min(int(0.005 * self.sample_rate), num_samples // 4)
        if fade > 0:
            tone[:fade] *= np.linspace(0, 1, fade)
            tone[-fade:] *= np.linspace(1, 0, fade)
        return tone * 0.85

    def _span_word_set(self, pii_spans):
        spans_by_word = {}
        for span in pii_spans:
            for w in span.text.split():
                key = w.lower().strip(".,!?'\"")
                if key:
                    spans_by_word[key] = span
        return spans_by_word

    def redact_audio(self, audio_buffer, word_timestamps, pii_spans):
        signal = audio_buffer.astype(np.float64) if not isinstance(audio_buffer, np.ndarray) else audio_buffer.astype(np.float64)
        if np.max(np.abs(signal)) > 1.0:
            signal = signal / 32768.0
        redacted = signal.copy()
        span_map = self._span_word_set(pii_spans)

        for w in word_timestamps:
            clean = w["word"].lower().strip(".,!?'\"")
            if clean not in span_map:
                continue
            ss = int(round(w["start"] * self.sample_rate))
            se = int(round(w["end"] * self.sample_rate))
            se = min(se, len(redacted))
            if se - ss < 4:
                continue
            beep = self._beep(se - ss)
            redacted[ss:se] = beep[:se - ss]

        max_val = np.max(np.abs(redacted))
        if max_val > 1.0:
            redacted = redacted / max_val * 0.99
        return (redacted * 32767).astype(np.int16)


class RollingBuffer:
    def __init__(self, max_seconds=BUFFER_SECONDS, sample_rate=SAMPLE_RATE):
        self.max_samples = int(max_seconds * sample_rate)
        self.buffer = np.zeros(self.max_samples, dtype=np.int16)
        self.total_written = 0
        self.lock = threading.Lock()

    def _phys(self, logical_pos: int) -> int:
        return int(logical_pos) % self.max_samples

    def write(self, data):
        samples = np.frombuffer(data, dtype=np.int16)
        with self.lock:
            for s in samples:
                self.buffer[self._phys(self.total_written)] = s
                self.total_written += 1

    def get_total_written(self):
        with self.lock:
            return self.total_written

    def read_samples(self, start_sample: int, count: int) -> Optional[np.ndarray]:
        if count <= 0:
            return None
        with self.lock:
            if start_sample < 0:
                return None
            if self.total_written < start_sample + count:
                return None
            if self.total_written > self.max_samples and start_sample < self.total_written - self.max_samples:
                return None
            result = np.zeros(count, dtype=np.int16)
            for i in range(count):
                result[i] = self.buffer[self._phys(start_sample + i)]
            return result

    def get_window_at(self, pos: int, seconds=WINDOW_SECONDS) -> Optional[np.ndarray]:
        num_samples = int(seconds * SAMPLE_RATE)
        return self.read_samples(pos, num_samples)


class StreamingPipeline:
    def __init__(self, use_blackhole=False, blackhole_device_id=None,
                 context_mode="all", whitelist=None, audit=None, consent=False,
                 backend="pyaudio", output_lag=0.3, buffer_seconds=10.0,
                 echo_cancel=False, model_size="base"):
        print("=" * 60)
        print("  STREAMING PRIVACY PIPELINE")
        print("  Loading models...")
        print("=" * 60)

        print("\n1. Loading PII Filter (spaCy + Indian rules)...")
        self.pii = PIIMask(context_mode=context_mode)

        print(f"\n2. Loading Whisper ({model_size})...")
        self.transcriber = LocalTranscriber(model_size=model_size)

        print("\n3. Loading Speaker Diarizer...")
        self.diarizer = SpeakerDiarizer()

        self.backend = backend
        self.audio = None
        if backend == "pyaudio" or use_blackhole:
            self.audio = pyaudio.PyAudio()
        self.buffer = RollingBuffer(max_seconds=buffer_seconds)
        self.redactor = AudioRedactor()
        self.use_blackhole = use_blackhole
        self.blackhole_device_id = blackhole_device_id
        self.output_lag = max(output_lag, WINDOW_SECONDS + 2.0)

        self.input_stream = None
        self.output_stream = None
        self.recording = False
        self.sd = None

        if backend == "sounddevice":
            try:
                import sounddevice as sd
                self.sd = sd
                print(f"  Using sounddevice backend (latency: {sd.query_devices(sd.default.device[0])['name']})")
            except ImportError:
                print("  sounddevice not installed, falling back to PyAudio")
                self.backend = "pyaudio"
                self.audio = pyaudio.PyAudio()

        self.whitelist = whitelist or Whitelist()
        self.audit = audit or AuditLog(enabled=False)
        self.consent_mode = consent
        self.consent_granted = True
        self.consent_lock = threading.Lock()

        self.echo_cancel = echo_cancel
        self.aec = AcousticEchoCanceller() if echo_cancel else None
        self.mic_ref_buffer = deque(maxlen=int(SAMPLE_RATE * 1.0))

        self.output_queue = queue.Queue(maxsize=3)
        self.session_stats = {"total": 0, "redacted": 0, "pii_counts": {}}

        if not use_blackhole and not echo_cancel:
            print("\n  ⚠️  WARNING: Streaming without headphones or BlackHole will cause echo.")
            print("     Use --echo-cancel to enable acoustic echo cancellation, or")
            print("     use --blackhole to route audio to apps (Zoom/Meet), or")
            print("     wear headphones to prevent mic picking up speaker output.\n")
        print("\n  System ready.\n")

    def _toggle_consent(self):
        with self.consent_lock:
            self.consent_granted = not self.consent_granted
        status = "ACTIVE" if self.consent_granted else "PAUSED"
        print(f"\n  >>> Redaction {'RESUMED' if self.consent_granted else 'PAUSED'} <<<")

    def _list_blackhole_devices(self):
        blackhole_devices = []
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            name = info["name"].lower()
            if "blackhole" in name:
                blackhole_devices.append((i, info))
        return blackhole_devices

    def _record_loop(self):
        if self.backend == "sounddevice" and self.sd:
            self._record_loop_sounddevice()
        else:
            self._record_loop_pyaudio()

    def _record_loop_pyaudio(self):
        self.input_stream = self.audio.open(
            format=FORMAT, channels=CHANNELS,
            rate=SAMPLE_RATE, input=True,
            frames_per_buffer=CHUNK,
        )
        while self.recording:
            try:
                data = self.input_stream.read(CHUNK, exception_on_overflow=False)
                if self.echo_cancel and len(self.mic_ref_buffer) >= CHUNK * 2:
                    ref_bytes = b''.join(list(self.mic_ref_buffer)[-CHUNK * 2:])
                    ref_samples = np.frombuffer(ref_bytes, dtype=np.int16)
                    mic_samples = np.frombuffer(data, dtype=np.int16)
                    cancelled = self.aec.process(mic_samples, ref_samples[:len(mic_samples)])
                    self.buffer.write(cancelled.tobytes())
                else:
                    self.buffer.write(data)
            except OSError as e:
                print(f"\n  [Audio capture error: {e}]")
                time.sleep(0.01)

    def _record_loop_sounddevice(self):
        def callback(in_data, frames, time_info, status):
            if status:
                print(f"\n  [SD status: {status}]")
            if self.recording:
                if in_data.ndim > 1 and in_data.shape[1] > 1:
                    mono = in_data.mean(axis=1, dtype=np.int16)
                else:
                    mono = in_data.flatten()
                if self.echo_cancel and len(self.mic_ref_buffer) >= CHUNK * 2:
                    ref_bytes = b''.join(list(self.mic_ref_buffer)[-CHUNK * 2:])
                    ref_samples = np.frombuffer(ref_bytes, dtype=np.int16)
                    cancelled = self.aec.process(mono, ref_samples[:len(mono)])
                    self.buffer.write(cancelled.tobytes())
                else:
                    self.buffer.write(mono.tobytes())

        with self.sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1 if CHANNELS == 1 else 2,
            blocksize=CHUNK,
            callback=callback,
            dtype='int16',
            latency='low',
        ):
            while self.recording:
                time.sleep(0.1)

    def _output_loop(self):
        self._open_output_stream()
        if self.output_stream is None:
            print("  [Output stream unavailable - queue will fill but not play]")
            return

        while self.recording:
            try:
                redacted_audio = self.output_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            samples = redacted_audio.astype(np.int16)
            pos = 0
            while pos < len(samples):
                end = min(pos + CHUNK_OUTPUT, len(samples))
                chunk = samples[pos:end]
                try:
                    self.output_stream.write(chunk.tobytes())
                except OSError as e:
                    print(f"\n  [Audio output error: {e}]")
                    time.sleep(0.01)
                    break
                pos = end

    def _format_speaker_output(self, words_with_speakers):
        if not words_with_speakers:
            return ""
        current_speaker = None
        parts = []
        for ws in words_with_speakers:
            if ws.speaker != current_speaker:
                current_speaker = ws.speaker
                short = ws.speaker.replace("SPEAKER_", "S")
                parts.append(f"[{short}]")
            parts.append(ws.word)
        return " ".join(parts)

    def _process_window_at(self, sample_pos: int):
        audio_samples = self.buffer.get_window_at(sample_pos, WINDOW_SECONDS)
        if audio_samples is None or len(audio_samples) == 0:
            return None

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_samples.tobytes())
            tmp_path = tmp.name

            text, word_timestamps = self.transcriber.transcribe_with_timestamps(tmp_path)
            speaker_segments = self.diarizer.diarize(tmp_path)
            words_with_speakers = self.diarizer.assign_words_to_speakers(
                word_timestamps, speaker_segments
            )
        finally:
            os.unlink(tmp.name)

        if not text:
            return {
                "original_text": "",
                "redacted_text": "",
                "spans": [],
                "word_timestamps": [],
                "words_with_speakers": [],
                "redacted_audio": audio_samples.astype(np.int16),
            }

        redacted_text, spans = self.pii.analyze(text)
        spans = [s for s in spans if not self.whitelist.contains_any(s.text)]

        redacted_audio = None
        if spans:
            redacted_audio = self.redactor.redact_audio(
                audio_samples.astype(np.float64), word_timestamps, spans
            )

        speaker_text = self._format_speaker_output(words_with_speakers)
        self.audit.log_event(
            original_text=text,
            redacted_text=redacted_text,
            spans=spans,
            speaker_info=speaker_text[:100],
        )

        print(f"\n  Heard:    {text[:100]}")
        print(f"  Speakers: {speaker_text[:100]}")
        print(f"  Redacted: {redacted_text[:100]}")

        if spans:
            summary = self.pii.get_redaction_summary(spans)
            print(f"  Blocked:  {summary}")
            self.session_stats["redacted"] += 1

        self.session_stats["total"] += 1
        for span in spans:
            self.session_stats["pii_counts"][span.label] = \
                self.session_stats["pii_counts"].get(span.label, 0) + 1

        if redacted_audio is None:
            redacted_audio = audio_samples.astype(np.int16)

        return {
            "original_text": text,
            "redacted_text": redacted_text,
            "spans": spans,
            "word_timestamps": word_timestamps,
            "words_with_speakers": words_with_speakers,
            "redacted_audio": redacted_audio,
        }

    def _open_output_stream(self):
        if self.audio is None:
            self.audio = pyaudio.PyAudio()

        device_index = None
        if self.use_blackhole:
            bh_devices = self._list_blackhole_devices()
            if not bh_devices:
                print("  Warning: No BlackHole device found. Falling back to default output.")
            else:
                if self.blackhole_device_id is not None:
                    for idx, info in bh_devices:
                        if idx == self.blackhole_device_id:
                            device_index = idx
                            break
                if device_index is None:
                    device_index = bh_devices[0][0]
                dev_name = self.audio.get_device_info_by_index(device_index)["name"]
                print(f"  Using BlackHole device: {dev_name} (index {device_index})")

        try:
            self.output_stream = self.audio.open(
                format=FORMAT, channels=CHANNELS,
                rate=SAMPLE_RATE, output=True,
                output_device_index=device_index,
                frames_per_buffer=CHUNK,
            )
        except OSError as e:
            print(f"  [Failed to open output stream: {e}]")
            self.output_stream = None

    def run(self):
        self.recording = True

        record_thread = threading.Thread(target=self._record_loop, daemon=True)
        record_thread.start()

        output_thread = threading.Thread(target=self._output_loop, daemon=True)
        output_thread.start()

        print("  Streaming privacy filter active.")
        print("  Model: {} | Window: {}s | Output delay: ~{}s".format(
            "whisper", WINDOW_SECONDS, int(WINDOW_SECONDS + 2)))
        if self.echo_cancel:
            print("  Echo cancellation: ACTIVE (NLMS adaptive filter)")
        print("  Queue-based: every window processed before playback (no missed redactions)")
        if self.use_blackhole:
            print("  Output routed to BlackHole (select in Zoom/Meet settings).")
        if self.consent_mode:
            print("  Consent mode: redaction is ACTIVE. Press 'c' then ENTER to toggle.")
        print("  Press Ctrl+C to stop.\n")

        try:
            window_samples = int(WINDOW_SECONDS * SAMPLE_RATE)
            next_output_pos = 0
            while True:
                total_written = self.buffer.get_total_written()
                needed = next_output_pos + window_samples
                if total_written < needed:
                    time.sleep(0.1)
                    continue

                if self.consent_mode:
                    with self.consent_lock:
                        grant = self.consent_granted
                    if not grant:
                        time.sleep(HOP_SECONDS)
                        continue

                result = self._process_window_at(next_output_pos)
                if result:
                    try:
                        self.output_queue.put(result["redacted_audio"], timeout=1.0)
                    except queue.Full:
                        print("  [Warning: output queue full - dropping window]")

                next_output_pos += window_samples

        except KeyboardInterrupt:
            print("\n  Stopping...")
        finally:
            self.recording = False
            self.audit.flush()
            if self.input_stream:
                try:
                    self.input_stream.stop_stream()
                    self.input_stream.close()
                except OSError:
                    pass
            if self.output_stream:
                try:
                    self.output_stream.stop_stream()
                    self.output_stream.close()
                except OSError:
                    pass
            self.audio.terminate()
            self._print_session_stats()

    def _print_session_stats(self):
        print("\n" + "=" * 60)
        print("  SESSION SUMMARY")
        print("=" * 60)
        print(f"  Total windows   : {self.session_stats['total']}")
        print(f"  With PII blocked : {self.session_stats['redacted']}")
        if self.session_stats["pii_counts"]:
            print("  PII breakdown:")
            for label, count in sorted(self.session_stats["pii_counts"].items()):
                print(f"    {label:<15}: {count}")
        print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Streaming Privacy Pipeline")
    parser.add_argument("--blackhole", action="store_true",
                        help="Route output to BlackHole virtual microphone")
    parser.add_argument("--blackhole-device", type=int, default=None,
                        help="BlackHole device index (auto-detect if not specified)")
    args = parser.parse_args()

    pipeline = StreamingPipeline(
        use_blackhole=args.blackhole,
        blackhole_device_id=args.blackhole_device,
    )
    pipeline.run()

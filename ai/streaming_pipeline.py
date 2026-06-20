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
    def __init__(self, max_seconds=WINDOW_SECONDS + 1, sample_rate=SAMPLE_RATE):
        self.max_samples = int(max_seconds * sample_rate)
        self.buffer = np.zeros(self.max_samples, dtype=np.int16)
        self.write_pos = 0
        self.total_written = 0
        self.lock = threading.Lock()

    def write(self, data):
        samples = np.frombuffer(data, dtype=np.int16)
        with self.lock:
            for s in samples:
                self.buffer[self.write_pos] = s
                self.write_pos = (self.write_pos + 1) % self.max_samples
                self.total_written += 1

    def get_window(self, seconds=WINDOW_SECONDS):
        num_samples = int(seconds * SAMPLE_RATE)
        with self.lock:
            if self.total_written < self.max_samples:
                if self.total_written < num_samples:
                    return None
                start = 0
                end = min(num_samples, self.total_written)
                return self.buffer[start:end].copy()
            read_start = (self.write_pos - num_samples) % self.max_samples
            if read_start + num_samples <= self.max_samples:
                return self.buffer[read_start:read_start + num_samples].copy()
            part1 = self.buffer[read_start:]
            part2 = self.buffer[:num_samples - len(part1)]
            return np.concatenate([part1, part2])

    def get_window_count(self):
        return self.total_written


class StreamingPipeline:
    def __init__(self, use_blackhole=False, blackhole_device_id=None,
                 context_mode="all", whitelist=None, audit=None, consent=False):
        print("=" * 60)
        print("  STREAMING PRIVACY PIPELINE")
        print("  Loading models...")
        print("=" * 60)

        print("\n1. Loading PII Filter (spaCy + Indian rules)...")
        self.pii = PIIMask(context_mode=context_mode)

        print("\n2. Loading Whisper (small)...")
        self.transcriber = LocalTranscriber(model_size="small")

        print("\n3. Loading Speaker Diarizer...")
        self.diarizer = SpeakerDiarizer()

        self.audio = pyaudio.PyAudio()
        self.buffer = RollingBuffer()
        self.redactor = AudioRedactor()
        self.use_blackhole = use_blackhole
        self.blackhole_device_id = blackhole_device_id

        self.input_stream = None
        self.output_stream = None
        self.recording = False
        self.processing = False

        self.whitelist = whitelist or Whitelist()
        self.audit = audit or AuditLog(enabled=False)
        self.consent_mode = consent
        self.consent_granted = True
        self.consent_lock = threading.Lock()

        self.session_stats = {"total": 0, "redacted": 0, "pii_counts": {}}
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
        self.input_stream = self.audio.open(
            format=FORMAT, channels=CHANNELS,
            rate=SAMPLE_RATE, input=True,
            frames_per_buffer=CHUNK,
        )
        while self.recording:
            data = self.input_stream.read(CHUNK, exception_on_overflow=False)
            self.buffer.write(data)

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

    def _process_window(self, audio_samples):
        if audio_samples is None or len(audio_samples) == 0:
            return None

        import tempfile
        import os
        import wave

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
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

        os.unlink(tmp_path)

        if not text:
            return None

        redacted_text, spans = self.pii.analyze(text)

        spans = [s for s in spans if not self.whitelist.contains_any(s.text)]

        if spans:
            redacted_audio = self.redactor.redact_audio(
                audio_samples.astype(np.float64), word_timestamps, spans
            )
        else:
            redacted_audio = audio_samples

        return {
            "original_text": text,
            "redacted_text": redacted_text,
            "spans": spans,
            "redacted_audio": redacted_audio,
            "word_timestamps": word_timestamps,
            "words_with_speakers": words_with_speakers,
        }

    def _open_output_stream(self):
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

        self.output_stream = self.audio.open(
            format=FORMAT, channels=CHANNELS,
            rate=SAMPLE_RATE, output=True,
            output_device_index=device_index,
            frames_per_buffer=CHUNK,
        )

    def run(self):
        self._open_output_stream()
        self.recording = True

        record_thread = threading.Thread(target=self._record_loop, daemon=True)
        record_thread.start()

        print("  Streaming privacy filter active.")
        print("  Processing in {}-second windows every {:.1f}s".format(WINDOW_SECONDS, HOP_SECONDS))
        if self.use_blackhole:
            print("  Output routed to BlackHole (select in Zoom/Meet settings).")
        if self.consent_mode:
            print("  Consent mode: redaction is ACTIVE. Press 'c' then ENTER to toggle.")
        print("  Press Ctrl+C to stop.\n")

        try:
            last_window_count = 0
            while True:
                time.sleep(HOP_SECONDS)
                current_count = self.buffer.get_window_count()
                if current_count == last_window_count:
                    continue
                last_window_count = current_count

                if self.consent_mode:
                    with self.consent_lock:
                        grant = self.consent_granted
                    if not grant:
                        raw_samples = self.buffer.get_window(WINDOW_SECONDS)
                        if raw_samples is not None:
                            self.output_stream.write(raw_samples.tobytes())
                        continue

                audio_samples = self.buffer.get_window(WINDOW_SECONDS)
                if audio_samples is None:
                    continue

                self.processing = True
                result = self._process_window(audio_samples)
                self.processing = False

                if result is None:
                    continue

                text = result["original_text"]
                redacted = result["redacted_text"]
                spans = result["spans"]
                redacted_audio = result["redacted_audio"]
                words_with_speakers = result.get("words_with_speakers", [])

                speaker_text = self._format_speaker_output(words_with_speakers)

                self.audit.log_event(
                    original_text=text,
                    redacted_text=redacted,
                    spans=spans,
                    speaker_info=speaker_text[:100],
                )

                print(f"\n  Heard:    {text[:100]}")
                print(f"  Speakers: {speaker_text[:100]}")
                print(f"  Redacted: {redacted[:100]}")

                if spans:
                    summary = self.pii.get_redaction_summary(spans)
                    print(f"  Blocked:  {summary}")
                    self.session_stats["redacted"] += 1

                self.output_stream.write(redacted_audio.tobytes())

                self.session_stats["total"] += 1
                for span in spans:
                    self.session_stats["pii_counts"][span.label] = \
                        self.session_stats["pii_counts"].get(span.label, 0) + 1

        except KeyboardInterrupt:
            print("\n  Stopping...")
        finally:
            self.recording = False
            self.audit.flush()
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
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

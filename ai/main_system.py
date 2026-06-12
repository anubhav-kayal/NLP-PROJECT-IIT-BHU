import sys
import wave
import struct
import math
import tempfile
import os
import time
import pyaudio
from pii_mask import PIIMask
from transcriber import LocalTranscriber
from streaming_pipeline import StreamingPipeline

SAMPLE_RATE    = 16000
CHANNELS       = 1
FORMAT         = pyaudio.paInt16
CHUNK          = 1024
RECORD_SECONDS = 4
BEEP_DURATION  = 0.35

BEEP_FREQUENCIES = {
    "PERSON":   880,
    "PER":      880,
    "AADHAAR":  660,
    "PAN":      660,
    "PHONE":    520,
    "UPI_ID":   520,
    "EMAIL":    520,
    "BANK_ACC": 660,
    "IFSC":     660,
    "ORG":      440,
    "GPE":      440,
    "LOC":      440,
    "DEFAULT":  440,
}


class FixedRecordAssistant:

    def __init__(self):
        print("=" * 60)
        print("  PRIVACY-PRESERVING VOICE ASSISTANT (Fixed-Record Mode)")
        print("  Loading models...")
        print("=" * 60)

        print("\n1. Loading PII Filter (spaCy + Indian rules)...")
        self.pii = PIIMask()

        print("\n2. Loading Whisper (small)...")
        self.transcriber = LocalTranscriber(model_size="small")

        self.audio = pyaudio.PyAudio()
        self.session_stats = {"total": 0, "redacted": 0, "pii_counts": {}}
        print("\n  System ready.\n")

    def _generate_beep(self, frequency, duration):
        num_samples = int(SAMPLE_RATE * duration)
        samples = []
        fade = int(SAMPLE_RATE * 0.02)
        for i in range(num_samples):
            envelope = 1.0
            if i < fade:
                envelope = i / fade
            elif i > num_samples - fade:
                envelope = (num_samples - i) / fade
            val = envelope * 0.6 * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)
            samples.append(int(val * 32767))
        return struct.pack(f"{num_samples}h", *samples)

    def _record(self, seconds=RECORD_SECONDS):
        stream = self.audio.open(
            format=FORMAT, channels=CHANNELS,
            rate=SAMPLE_RATE, input=True,
            frames_per_buffer=CHUNK
        )
        frames = []
        total_chunks = int(SAMPLE_RATE / CHUNK * seconds)
        for i in range(total_chunks):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            filled = int(30 * i / total_chunks)
            bar = "█" * filled + "░" * (30 - filled)
            print(f"\r  [{bar}] Recording... {i * CHUNK // SAMPLE_RATE}s", end="", flush=True)
        print()
        stream.stop_stream()
        stream.close()

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return tmp.name

    def _play_beep(self, span):
        freq = BEEP_FREQUENCIES.get(span.label, BEEP_FREQUENCIES["DEFAULT"])
        duration = max(BEEP_DURATION, len(span.text.split()) * 0.25)
        beep_data = self._generate_beep(freq, duration)
        stream = self.audio.open(
            format=FORMAT, channels=CHANNELS,
            rate=SAMPLE_RATE, output=True
        )
        stream.write(beep_data)
        stream.stop_stream()
        stream.close()

    def _update_stats(self, spans):
        self.session_stats["total"] += 1
        if spans:
            self.session_stats["redacted"] += 1
        for span in spans:
            self.session_stats["pii_counts"][span.label] = \
                self.session_stats["pii_counts"].get(span.label, 0) + 1

    def _print_session_stats(self):
        print("\n" + "=" * 60)
        print("  SESSION SUMMARY")
        print("=" * 60)
        print(f"  Total utterances : {self.session_stats['total']}")
        print(f"  With PII blocked : {self.session_stats['redacted']}")
        if self.session_stats["pii_counts"]:
            print("  PII breakdown:")
            for label, count in self.session_stats["pii_counts"].items():
                print(f"    {label:<15}: {count}")
        print("=" * 60)

    def run(self):
        print("Press ENTER to speak, 'q' + ENTER to quit.\n")
        while True:
            try:
                cmd = input("  [ENTER to speak / q to quit] > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd == "q":
                break

            print("\n  Listening for 4 seconds — speak now...")
            wav_path = self._record()

            print("  Transcribing...")
            text, word_timestamps = self.transcriber.transcribe_with_timestamps(wav_path)
            os.unlink(wav_path)

            if not text:
                print("  (Nothing heard)\n")
                continue

            redacted, spans = self.pii.analyze(text)

            print(f"\n  Heard:    {text}")
            print(f"  Redacted: {redacted}")

            if spans:
                summary = self.pii.get_redaction_summary(spans)
                print(f"  Blocked:  {summary}")
                print(f"  [BEEP played for {len(spans)} PII item(s)]")
                LocalTranscriber.log_word_timestamps(word_timestamps, spans)

                for span in spans:
                    self._play_beep(span)
                    time.sleep(0.05)
            else:
                print("  [No PII detected]\n")

            self._update_stats(spans)

        self._print_session_stats()
        self.audio.terminate()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Privacy-Preserving Voice Assistant")
    parser.add_argument("--fixed", action="store_true",
                        help="Use fixed 4-second recording mode (legacy)")
    parser.add_argument("--blackhole", action="store_true",
                        help="Route streaming output to BlackHole virtual microphone")
    parser.add_argument("--blackhole-device", type=int, default=None,
                        help="BlackHole device index")
    args = parser.parse_args()

    if args.fixed:
        assistant = FixedRecordAssistant()
        assistant.run()
    else:
        pipeline = StreamingPipeline(
            use_blackhole=args.blackhole,
            blackhole_device_id=args.blackhole_device,
        )
        pipeline.run()

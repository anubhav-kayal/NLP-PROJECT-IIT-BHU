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
from diarization import SpeakerDiarizer
from whitelist import Whitelist
from audit_log import AuditLog

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
    "CASTE_RELIGION": 440,
    "MEDICAL":  440,
    "DEFAULT":  440,
}


class FixedRecordAssistant:

    def __init__(self, context_mode="all", whitelist=None, audit=None, consent=False):
        print("=" * 60)
        print("  PRIVACY-PRESERVING VOICE ASSISTANT (Fixed-Record Mode)")
        print("  Loading models...")
        print("=" * 60)

        print("\n1. Loading PII Filter (spaCy + Indian rules)...")
        self.pii = PIIMask(context_mode=context_mode)

        print("\n2. Loading Whisper (small)...")
        self.transcriber = LocalTranscriber(model_size="small")

        print("\n3. Loading Speaker Diarizer...")
        self.diarizer = SpeakerDiarizer()

        self.audio = pyaudio.PyAudio()
        self.session_stats = {"total": 0, "redacted": 0, "pii_counts": {}}
        self.whitelist = whitelist or Whitelist()
        self.audit = audit or AuditLog(enabled=False)
        self.consent_mode = consent
        self.consent_granted = True
        print("\n  System ready.\n")

    def _toggle_consent(self):
        self.consent_granted = not self.consent_granted
        status = "ACTIVE" if self.consent_granted else "PAUSED"
        print(f"\n  >>> Redaction {'RESUMED' if self.consent_granted else 'PAUSED'} <<<")

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
        if self.consent_mode:
            print("  Consent mode: redaction is ACTIVE. Type 'c' to toggle pause/resume.\n")
        while True:
            try:
                cmd = input("  [ENTER to speak / q to quit] > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd == "q":
                break
            if cmd == "c" and self.consent_mode:
                self._toggle_consent()
                continue

            if self.consent_mode and not self.consent_granted:
                print("  [Redaction paused — audio will pass through]\n")
                continue

            print("\n  Listening for 4 seconds — speak now...")
            wav_path = self._record()

            print("  Transcribing...")
            text, word_timestamps = self.transcriber.transcribe_with_timestamps(wav_path)

            print("  Diarizing speakers...")
            speaker_segments = self.diarizer.diarize(wav_path)
            words_with_speakers = self.diarizer.assign_words_to_speakers(
                word_timestamps, speaker_segments
            )

            os.unlink(wav_path)

            if not text:
                print("  (Nothing heard)\n")
                continue

            redacted, spans = self.pii.analyze(text)

            spans = [s for s in spans if not self.whitelist.contains_any(s.text)]

            current_speaker = None
            speaker_parts = []
            for ws in words_with_speakers:
                if ws.speaker != current_speaker:
                    current_speaker = ws.speaker
                    short = ws.speaker.replace("SPEAKER_", "S")
                    speaker_parts.append(f"[{short}]")
                speaker_parts.append(ws.word)
            speaker_text = " ".join(speaker_parts)

            print(f"\n  Heard:    {text}")
            print(f"  Speakers: {speaker_text}")
            print(f"  Redacted: {redacted}")

            self.audit.log_event(
                original_text=text,
                redacted_text=redacted,
                spans=spans,
                speaker_info=speaker_text[:100],
            )

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
    parser.add_argument("--context-mode", choices=["all", "personal", "public"],
                        default="all",
                        help="Redaction context mode (default: all)")
    parser.add_argument("--consent", action="store_true",
                        help="Enable consent mode (toggle redaction with 'c' key)")
    parser.add_argument("--audit", action="store_true",
                        help="Enable encrypted local audit log")
    parser.add_argument("--view-audit", action="store_true",
                        help="Decrypt and view the audit log")
    parser.add_argument("--whitelist-add", type=str, default=None,
                        help="Add a term to the whitelist")
    parser.add_argument("--whitelist-remove", type=str, default=None,
                        help="Remove a term from the whitelist")
    parser.add_argument("--whitelist-list", action="store_true",
                        help="List all whitelisted terms")
    parser.add_argument("--redact", type=str, default=None,
                        help="Redact PII from an audio file (WAV/MP3)")
    parser.add_argument("--redact-transcript", type=str, default=None,
                        help="Redact PII from a transcript file (VTT/TXT)")
    parser.add_argument("--batch-dir", type=str, default=None,
                        help="Batch process all audio/transcript files in a directory")
    parser.add_argument("--dashboard", action="store_true",
                        help="Start the localhost web dashboard")
    parser.add_argument("--dashboard-port", type=int, default=5000,
                        help="Dashboard port (default: 5000)")
    parser.add_argument("--backend", choices=["pyaudio", "sounddevice"], default="pyaudio",
                        help="Audio capture backend (default: pyaudio)")
    parser.add_argument("--output-lag", type=float, default=0.3,
                        help="Output lag in seconds (default: 0.3, lower = less latency)")
    parser.add_argument("--buffer-seconds", type=float, default=10.0,
                        help="Ring buffer size in seconds (default: 10.0)")
    parser.add_argument("--echo-cancel", action="store_true",
                        help="Enable acoustic echo cancellation (NLMS adaptive filter)")
    parser.add_argument("--model-size", choices=["tiny", "base", "small", "medium", "large"],
                        default="base",
                        help="Whisper model size (default: base, faster than small for streaming)")
    args = parser.parse_args()

    if args.view_audit:
        AuditLog.print_log()
        sys.exit(0)

    wl = Whitelist()
    if args.whitelist_add:
        wl.add(args.whitelist_add)
        print(f"  Added '{args.whitelist_add}' to whitelist.")
        sys.exit(0)
    if args.whitelist_remove:
        wl.remove(args.whitelist_remove)
        print(f"  Removed '{args.whitelist_remove}' from whitelist.")
        sys.exit(0)
    if args.whitelist_list:
        terms = wl.list()
        if terms:
            print("  Whitelisted terms:")
            for t in terms:
                print(f"    - {t}")
        else:
            print("  Whitelist is empty.")
        sys.exit(0)

    if args.redact:
        from file_redactor import FileRedactor
        redactor = FileRedactor()
        result = redactor.redact_file(args.redact, context_mode=args.context_mode)
        print(f"\n  Original: {result['original_text']}")
        print(f"  Redacted: {result['redacted_text']}")
        print(f"  PII found: {result['pii_count']}")
        print(f"  Outputs: {result['output_wav']}, {result['output_json']}, {result['output_txt']}")
        sys.exit(0)

    if args.redact_transcript:
        from transcript_processor import TranscriptProcessor
        processor = TranscriptProcessor()
        result = processor.process_transcript(args.redact_transcript, context_mode=args.context_mode)
        print(f"\n  Original: {result['original_text'][:200]}")
        print(f"  Redacted: {result['redacted_text'][:200]}")
        print(f"  PII found: {result['pii_count']}")
        print(f"  Outputs: {result['output_json']}, {result['output_txt']}, {result['output_vtt']}")
        sys.exit(0)

    if args.batch_dir:
        from batch_processor import BatchProcessor
        processor = BatchProcessor()
        report = processor.process_directory(args.batch_dir, context_mode=args.context_mode)
        s = report["summary"]
        print(f"\n  Batch Summary:")
        print(f"    Audio: {s['audio_success']}/{s['audio_files']} OK")
        print(f"    Transcripts: {s['transcript_success']}/{s['transcript_files']} OK")
        print(f"    Total PII detected: {s['total_pii_detected']}")
        sys.exit(0)

    if args.dashboard:
        from dashboard import DashboardServer
        server = DashboardServer(port=args.dashboard_port)
        server.start()
        sys.exit(0)

    audit = AuditLog(enabled=args.audit)

    if args.fixed:
        assistant = FixedRecordAssistant(
            context_mode=args.context_mode,
            whitelist=wl,
            audit=audit,
            consent=args.consent,
        )
        assistant.run()
    else:
        pipeline = StreamingPipeline(
            use_blackhole=args.blackhole,
            blackhole_device_id=args.blackhole_device,
            context_mode=args.context_mode,
            whitelist=wl,
            audit=audit,
            consent=args.consent,
            backend=args.backend,
            output_lag=args.output_lag,
            buffer_seconds=args.buffer_seconds,
            echo_cancel=args.echo_cancel,
            model_size=args.model_size,
        )
        pipeline.run()

    if args.audit:
        audit.flush()

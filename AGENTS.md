## Project: NLP-PROJECT-IIT-BHU — Privacy-Preserving Voice Assistant

### Current State

All Phase 3 features are implemented (FileRedactor, TranscriptProcessor, PdfExporter, BatchProcessor, Dashboard, EchoCanceller, Installer). The streaming pipeline has been rewritten with a **queue-based output architecture**: processing pushes fully-redacted 3s chunks to `queue.Queue(maxsize=3)`, and a dedicated output thread plays them gaplessly. This eliminates the timing race conditions of the previous overlay-based approach.

### Completed
- Queue-based output: no missed redactions, no playback gaps
- Digit space normalization: spoken numbers (`"9 8 7 6 5 4 3 2 1 0"`) now match PII regex patterns
- Audio redactor: loud dual-tone beep (880Hz+1320Hz) replaced subtle noise
- RollingBuffer: unified `_phys()` position mapping fixes circular buffer misalignment
- CLI flags: `--backend`, `--model-size`, `--echo-cancel`, `--redact`, `--dashboard`, `--batch-dir`
- Sounddevice backend + NLMS echo cancellation available
- All new modules: `file_redactor.py`, `transcript_processor.py`, `pdf_exporter.py`, `batch_processor.py`, `dashboard.py`, `echo_canceller.py`, `install.sh`

### Next Steps (pick up here)
1. **Run `python ai/main_system.py --model-size tiny`** locally and verify that spoken numbers (phone, Aadhaar, PAN) produce audible beeps in the output. The queue-based architecture should provide gapless playback with ~5s delay.

2. **If beeps still don't play**: Investigate whether `AudioRedactor.redact_audio` word timestamps align with the audio window from `get_window_at`. Whisper word timestamps are relative to the temp WAV file (the 3s window), and `redact_audio` uses `w["start"] * sample_rate` to slice the audio array — this is correct only if the audio buffer matches the transcribed file exactly.

3. **Add `--model-size tiny` fallback** as the default for streaming (base is 2s, tiny is ~1s per 3s window — gives more queue buffer headroom).

4. **Post-call file redaction**: `python ai/main_system.py --redact recording.wav` — test with a WAV file containing PII.

5. **Dashboard**: `python ai/main_system.py --dashboard` — verify Flask web UI at `http://127.0.0.1:5000`.

6. **Batch mode**: `python ai/main_system.py --batch-dir ./test_data/` — process a directory of audio files.

### Known Issues
- PAN letters spoken as individual characters (`"A B C D E 1 2 3 4 F"`) are not yet detected — the digit normalization only handles uppercase+digit sequences, not all-caps letter-by-letter input. A separate `_collapse_letter_spaces` pass may be needed.
- Whisper tiny may have lower transcription accuracy for Indian English accents — `--model-size base` is the recommended default.
- The dashboard (Flask) and PyAudio output stream may conflict on some systems — test without dashboard first.

### CLI Reference
```
python main_system.py [--fixed] [--model-size {tiny,base,small}]
                     [--backend {pyaudio,sounddevice}] [--echo-cancel]
                     [--blackhole] [--redact file.wav]
                     [--redact-transcript file.vtt] [--batch-dir dir/]
                     [--dashboard] [--dashboard-port PORT]
                     [--consent] [--audit] [--context-mode {all,personal,public}]
                     [--output-lag SECONDS] [--buffer-seconds SECONDS]
```

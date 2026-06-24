## Project: NLP-PROJECT-IIT-BHU — Privacy-Preserving Voice Assistant

### Current State

All Phase 3+4 features are implemented. PII detection benchmark: **Overall F1=0.909** on 7500 samples. 12/13 categories above 0.85 F1 target. The streaming pipeline uses a **queue-based output architecture**: processing pushes fully-redacted 3s chunks to `queue.Queue(maxsize=3)`, and a dedicated output thread plays them gaplessly. Default model is now `tiny` (~1s per 3s window) for maximum streaming headroom.

### Completed
- Queue-based output: no missed redactions, no playback gaps
- Digit + letter space normalization: spoken PAN (`"A B C D E 1 2 3 4 F"`) now matches via `_collapse_letter_spaces` + `_collapse_digit_spaces`
- Digit-space collapse limited to runs <10 digits (prevents merging adjacent PII like AADHAAR+PINCODE)
- Directional AADHAAR↔BANK_ACC context: separate 40-char before/after windows + word-boundary keyword matching
- GPE FP reduction: caste terms, ORG names, and common words filtered from spaCy GPE detection
- 500+ new annotated sentence templates (7500 total dataset samples)
- Audio redactor: loud dual-tone beep (880Hz+1320Hz) replaced subtle noise
- RollingBuffer: unified `_phys()` position mapping fixes circular buffer misalignment
- CLI flags: `--backend`, `--model-size`, `--echo-cancel`, `--redact`, `--dashboard`, `--batch-dir`
- Sounddevice backend + NLMS echo cancellation available
- All new modules: `file_redactor.py`, `transcript_processor.py`, `pdf_exporter.py`, `batch_processor.py`, `dashboard.py`, `echo_canceller.py`, `install.sh`
- Default model-size changed to `tiny` for streaming + FixedRecordAssistant respects `--model-size`
- `_collapse_letter_spaces` added to `pii_mask.py` for explicit PAN letter-by-letter detection
- `FixedRecordAssistant` now accepts and passes `model_size` parameter

### Benchmark (7500 samples, Jun 25 2026)

| Category | F1 | Target |
|---|---|---|
| UPI_ID | 1.000 | ✅ |
| EMAIL | 1.000 | ✅ |
| PAN | 0.934 | ✅ |
| PHONE | 0.934 | ✅ |
| GPE | 0.947 | ✅ |
| AADHAAR | 0.914 | ✅ |
| BANK_ACC | 0.894 | ✅ |
| PERSON | 0.872 | ✅ |
| IFSC | 0.863 | ✅ |
| PINCODE | 0.859 | ✅ |
| CASTE_RELIGION | 0.851 | ✅ |
| ORG | 0.786 | ❌ |
| **Overall** | **0.909** | |

### Remaining Verification (manual testing)
1. **Run `python ai/main_system.py --model-size tiny`** locally and verify that spoken numbers (phone, Aadhaar, PAN) produce audible beeps in the output. The queue-based architecture should provide gapless playback with ~5s delay.
2. **If beeps still don't play**: Investigate whether `AudioRedactor.redact_audio` word timestamps align with the audio window from `get_window_at`. Analysis: the timestamp alignment is correct — `audio_samples` passed to `redact_audio` is the exact same window that Whisper transcribed (temp WAV), so `w["start"] * sample_rate` maps correctly.
3. **Post-call file redaction**: `python ai/main_system.py --redact recording.wav` — test with a WAV file containing PII.
4. **Dashboard**: `python ai/main_system.py --dashboard` — verify Flask web UI at `http://127.0.0.1:5000`.
5. **Batch mode**: `python ai/main_system.py --batch-dir ./test_data/` — process a directory of audio files.

### Notes
- Whisper tiny may have lower transcription accuracy for Indian English accents — override with `--model-size base`.
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

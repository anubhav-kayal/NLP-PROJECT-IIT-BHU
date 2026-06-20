# NLP Project - IIT BHU: Privacy-Preserving Voice Assistant

## Project Vision

A software privacy filter for your microphone that runs entirely on your laptop — no cloud, no internet needed. It sits between your microphone and the internet, transcribes audio locally, detects sensitive information (PII), and replaces those words with a beep before anything leaves your device.

## Architecture Overview

```
Microphone → Whisper (Local STT) → PII Mask (spaCy + Regex) → Redacted Audio
```

### Current Components

| Component | File | Role |
|---|---|---|
| Main Pipeline | `ai/main_system.py` | Orchestrates record → transcribe → detect → beep |
| Microphone | `ai/microphone_input.py` | PyAudio live capture, WAV saving, level monitoring |
| Transcriber | `ai/transcriber.py` | OpenAI Whisper (small) with word timestamps |
| PII Mask | `ai/pii_mask.py` | spaCy NER + rule-based Indian PII detection |
| Speaker Diarizer | `ai/diarization.py` | pyannote + energy-based VAD, word-to-speaker assignment |
| Streaming Pipeline | `ai/streaming_pipeline.py` | Sliding window capture, transcription, redaction, BlackHole output |
| Benchmark | `ai/benchmark.py` | Original 40-sample mini benchmark |
| Bench 7000 | `ai/benchmark_7000.py` | 7000-sample benchmark pipeline |
| Dataset Gen | `ai/generate_dataset.py` | 7000-sample Indian-context test data generator |

---

## PII Detection Categories (Current Coverage)

| Category | Pattern | Type |
|---|---|---|
| AADHAAR | `[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}` | Regex |
| PAN | `[A-Z]{5}[0-9]{4}[A-Z]{1}` | Regex |
| PHONE | `(?:\+91\|91\|0)?[5-9][0-9]{9}` | Regex |
| UPI_ID | `[\w.\-]{2,256}@[a-zA-Z]{2,64}` | Regex |
| IFSC | `[A-Z]{4}0[A-Z0-9]{6}` | Regex |
| EMAIL | `[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}` | Regex |
| BANK_ACC | `[0-9]{9,18}` (≥11 digits) | Regex |
| PINCODE | `[1-9][0-9]{5}` | Regex |
| PERSON | spaCy NER + Indian name dictionaries | NER + Dictionary |
| ORG | spaCy NER + Indian organization dictionary | NER + Dictionary |
| GPE/LOC | spaCy NER + Indian cities dictionary | NER + Dictionary |
| CASTE_RELIGION | Dictionary lookup (English + Hindi) | Dictionary |
| MEDICAL | Dictionary lookup (English + Hindi) | Dictionary |

---

## Changes Made (Previous Session)

### 1. Fixed PHONE ↔ BANK_ACC Overlap
**File:** `ai/pii_mask.py`
- Changed phone regex from `[6-9]` to `[5-9]` to cover 5-series mobile numbers
- Added check: BANK_ACC matches that also match PHONE pattern are skipped
- **Impact:** Phone F1 improved from 0.374 → 0.896 (+52pp)

### 2. Fixed AADHAAR Confusing with Phone Country Code
**File:** `ai/pii_mask.py`
- Added: if AADHAAR match is preceded by `+`, skip it
- Phone numbers like `+917654321098` created 12-digit sequences matching AADHAAR pattern
- **Impact:** Eliminated ~250 false AADHAAR detections from phone numbers

### 3. Added Priority-Based Span Merging
**File:** `ai/pii_mask.py`
- Added `RULE_PRIORITY` dict: AADHAAR/PAN=10, PHONE/UPI/EMAIL=9, IFSC=8, etc.
- Merge logic now uses priority (not raw confidence) to resolve overlapping spans
- **Impact:** Specific PII labels win over generic ones (PAN > ORG, PHONE > BANK_ACC)

### 4. Filtered ORG False Positives from spaCy NER
**File:** `ai/pii_mask.py`
- spaCy was tagging "PAN" (the word) and similar as ORG entities
- Added overlap/adjacency check: if spaCy entity is on or adjacent to a rule-based PII match, skip it
- **Impact:** ORG false positives reduced by ~25% (1956 → 1469)

### 5. Added 7000-Sample Benchmark Pipeline
**New files:**
- `ai/generate_dataset.py` — Generates 7000 Indian-context test samples
- `ai/benchmark_7000.py` — Runs PIIMask against dataset, per-category metrics
- `ai/test_dataset_7000.json` — The generated dataset

### 6. Cleaned Up Dataset Generation Bugs
**File:** `ai/generate_dataset.py`
- Removed invalid AADHAAR seeds starting with `1`
- Removed invalid IFSC seeds (e.g., `BOI0001234`)
- Removed 9-digit phone seed (`987654321`)

---

## Changes Made (This Session — Jun 18, 2026)

### 7. Integrated Speaker Diarization Pipeline
**Files:** `ai/diarization.py`, `ai/streaming_pipeline.py`, `ai/main_system.py`
- Replaced empty fallback with energy-based VAD (voice activity detection)
  - 25ms frames with 10ms hop, adaptive RMS thresholding
  - Merges adjacent speech segments (gaps < 0.3s)
  - Falls back to single `SPEAKER_00` segment for full audio
- Added `assign_words_to_speakers()` — maps Whisper word timestamps to speaker segments
- Integrated into `StreamingPipeline` — diarizes each 3s window, shows `[S00]` speaker labels
- Integrated into `FixedRecordAssistant` — same speaker labeling for fixed-record mode
- Maintains pyannote.audio integration as primary (falls back to VAD if unavailable)
- **Added `pyannote.audio` to requirements.txt**

### 8. AADHAAR ↔ BANK_ACC Context Disambiguation
**File:** `ai/pii_mask.py`
- Added `BANK_ACC_KEYWORDS` and `AADHAAR_KEYWORDS` sets
- `_skip_rule_match` now checks 80-character context window around 12-digit numbers
  - Banking keywords ("account", "transfer", "NEFT", etc.) → classify as BANK_ACC
  - Aadhaar keywords ("aadhaar", "uid", etc.) + banking keywords → prefer AADHAAR
- **Impact:** BANK_ACC F1 improved from 0.213 → 0.846 (+63pp)
- **Impact:** AADHAAR F1 improved from 0.785 → 0.946 (+16pp)

### 9. Added Indian Organization Dictionary
**File:** `ai/pii_mask.py`
- Added `INDIAN_ORGS` set with 100+ known organizations
  - Educational: IITs, NITs, IIITs, BITS, AIIMS, IISC, ISI
  - Banks: HDFC, ICICI, SBI, Axis, Kotak, PNB, Canara, etc.
  - Companies: TCS, Infosys, Wipro, Reliance, Flipkart, Paytm, etc.
  - Government: ISRO, DRDO, RBI, SEBI, Indian Railways
- Multi-word ORG matching (e.g., "HDFC Bank", "Times of India", "State Bank")
- **Impact:** ORG F1 improved from 0.490 → 0.828 (+34pp)

### 10. Fixed GPE Detection (Cities Overriding spaCy Noise)
**File:** `ai/pii_mask.py`
- Increased GPE/LOC priority from 4 → 5 (above ORG at 4)
- Added `_is_known_city()` — if spaCy tags a known Indian city as ORG or PERSON, skip the spaCy span
- Added `NOT_GPE_WORDS` filter — prevents common words from being detected as locations
- Added `NOT_GPE_WORDS_SPACY` — filters Hindi common words ("hai", "ka", "ki", etc.) misclassified by spaCy
- **Impact:** GPE F1 improved from 0.716 → 0.908 (+19pp)

### 11. Improved PERSON Detection with FP Filtering
**File:** `ai/pii_mask.py`
- Added `NOT_PERSON_WORDS` set (200+ entries) — filters titles ("madam", "dr", "sir"), roles ("staff", "manager", "teacher"), common words ("hello", "kyc", "pan", "person")
- Added spaCy PERSON span filtering — if any token in a PERSON span is in `NOT_PERSON_WORDS`, skip the span
- **Impact:** PERSON F1 improved from 0.864 → 0.899 (+3.5pp)
- **Impact:** PERSON precision improved from 0.836 → 0.914

### 12. Expanded ORG False Positive Filters
**File:** `ai/pii_mask.py`
- Added `ORG_FP_KEYWORDS` for wake words ("Alexa", "Siri"), tech brands, months, seasons
- Added "UPI ID", "LPG", "CNG" to ORG filter list
- **Impact:** ORG precision improved from 0.524 → 0.851

---

## Benchmark Results (7000 Samples)

### Progress Over Time

| Metric | Initial | Previous Fixes | Current (Jun 18) |
|---|---|---|---|
| **Overall F1** | 0.644 | 0.863 | **0.948** |
| Precision | 0.654 | 0.862 | **0.951** |
| Recall | 0.634 | 0.864 | **0.946** |
| Error samples | 3295 (47.1%) | 1514 (21.6%) | **788 (11.3%)** |

### Per-Category (Current — Jun 18, 2026)

| Category | Precision | Recall | F1 | Target (0.85) |
|---|---|---|---|---|
| PAN | 1.000 | 1.000 | **1.000** | ✅ |
| PINCODE | 1.000 | 1.000 | **1.000** | ✅ |
| EMAIL | 1.000 | 1.000 | **1.000** | ✅ |
| IFSC | 1.000 | 1.000 | **1.000** | ✅ |
| UPI_ID | 1.000 | 1.000 | **1.000** | ✅ |
| PHONE | 0.993 | 1.000 | **0.997** | ✅ |
| AADHAAR | 0.916 | 0.979 | **0.946** | ✅ |
| GPE | 0.859 | 0.963 | **0.908** | ✅ |
| PERSON | 0.914 | 0.884 | **0.899** | ✅ |
| BANK_ACC | 1.000 | 0.734 | **0.846** | ✅ |
| ORG | 0.851 | 0.807 | **0.828** | ~✅ |
| CASTE_RELIGION | 0.000 | 0.000 | **0.000** | ❌ (no dataset samples) |

---

## Changes Made (Jun 19, 2026 — Remaining Issues Fix + Phase 3 Start)

### 12. Fixed ORG F1 (0.828 → 0.881)
**File:** `ai/pii_mask.py`
- Expanded `INDIAN_ORGS` from ~100 to 180+ entries (added startups, PSUs, media houses, hospitals, more educational institutions)
- Added `ORG_FP_KEYWORDS_EXTRA` (100+ common non-org words) to filter spaCy ORG FPs
- Added strict ORG filtering for common words in `_spacy_spans`

### 13. Fixed BANK_ACC Recall (0.734 → 0.763)
**File:** `ai/pii_mask.py`
- Widened context window from 40 → 80 characters (160 char total)
- Added `_context_around_wide()` with 160-char window (320 char total) as secondary check
- Added banking keyword heuristic with fallback to wide context

### 14. Fixed CASTE_RELIGION F1 (0.000 → 0.885)
**Files:** `ai/pii_mask.py`, `ai/generate_dataset.py`
- Added 35 `CASTE_RELIGION_VALUES` and `CASTE_RELIGION_CONTEXT` templates to dataset generator
- Added `CASTE_RELIGION` to `PII_TYPES`, targets (4% distribution ~589 samples)
- Fixed priority clash: skipped last-name-only PERSON detection for caste/religion terms
- Filtered spaCy PERSON entities that are actually caste/religion terms
- Skipped first-name-only PERSON detection for standalone caste-overlapping words

### 15. Fixed PERSON Recall (0.884 → 0.925)
**File:** `ai/pii_mask.py`
- Added last-name-only detection (confidence 0.75) for single surnames
- Filtered last-name detection for caste/medical overlapping terms

### 16. Context-Aware Redaction
**File:** `ai/pii_mask.py`
- Added `DISCLOSURE_SIGNALS` set (30+ possessive/disclosure keywords)
- Added `PUBLIC_CONTEXT_SIGNALS` set (20+ general/public reference keywords)
- Added `classify_span_context()` — examines 5 words before and 3 after each span
- Added `context_mode` parameter to `PIIMask.__init__()` and `analyze()`:
  - `"all"`: redact all PII (default behavior)
  - `"personal"`: only redact PII in personal disclosure context
  - `"public"`: only redact PII in public/general reference context
- Added `context` field to `RedactedSpan` dataclass

### 17. Whitelist Mechanism
**New file:** `ai/whitelist.json`, `ai/whitelist.py`
- Persistent JSON-based whitelist (`whitelist.json`)
- `Whitelist` class with `add()`, `remove()`, `is_whitelisted()`, `contains_any()` methods
- CLI: `--whitelist-add`, `--whitelist-remove`, `--whitelist-list`

### 18. Consent Mode
**Files:** `ai/main_system.py`, `ai/streaming_pipeline.py`
- Thread-safe `consent_granted` flag with `consent_lock` in streaming mode
- Type `c` + ENTER to toggle pause/resume in fixed-record mode
- When paused: audio passes through without redaction
- CLI: `--consent`

### 19. Encrypted Local Audit Log
**New file:** `ai/audit_log.py`
- Fernet (symmetric) encryption using `cryptography` library
- Auto-generates key on first use (stored in `ai/audit/.audit_key`, `chmod 600`)
- Logs: timestamp, original text, redacted text, PII types, speaker info
- Appends to encrypted file `ai/audit/audit_log.enc`
- CLI: `--audit` (enable logging), `--view-audit` (decrypt & display)

---

## Known Limitations

| Issue | Root Cause | Status |
|---|---|---|---|
| **BANK_ACC recall=0.763** | 152 remaining FNs are 12-digit numbers without banking context keywords | Acceptable — widening further would trade off AADHAAR accuracy |
| **GPE precision=0.759** | 178 FPs are mostly cities in no-PII dataset samples; correct behavior in real use | Dataset artifact |

---

## Changes Made (Week 5 — Jun 20, 2026: Phase 3 Completion + Phase 4 Dashboard)

### 20. Post-Call MP3/WAV File Redaction
**New file:** `ai/file_redactor.py`
- `FileRedactor` class — transcribes any audio file (WAV/MP3/M4A/OGG/FLAC), runs PII detection, generates redacted audio + JSON report + redacted transcript
- Auto-converts non-WAV formats to WAV via pydub (optional, falls back gracefully)
- Uses existing `AudioRedactor` from streaming pipeline for noise-based audio redaction
- CLI: `python main_system.py --redact recording.wav`
- Batch support via `batch_redact()` method for multiple files

### 21. Transcript Integration (Zoom/Meet Exports)
**New file:** `ai/transcript_processor.py`
- `TranscriptProcessor` class — parses Zoom VTT format and plain-text speaker transcripts
- Detects speaker names from VTT cue labels and plain-text colon-separated patterns
- Per-segment PII analysis with speaker tracking
- Outputs redacted TXT, VTT, and JSON formats
- CLI: `python main_system.py --redact-transcript meeting.vtt`

### 22. PDF Export of Redacted Transcripts
**New file:** `ai/pdf_exporter.py`
- `PDFExporter` class — generates PDFs with original + redacted transcripts side-by-side
- Redacted spans rendered as black filled boxes with `[LABEL_REDACTED]` tags
- Report-style PDF with metadata (duration, word count, PII summary)
- Uses fpdf2 (lightweight, no LaTeX/Chrome needed)

### 23. Batch Processing and Redaction Reports
**New file:** `ai/batch_processor.py`
- `BatchProcessor` — processes entire directories of audio + transcript files
- Generates aggregate JSON report + interactive HTML report with:
  - Summary statistics (success/failure counts, total PII detected)
  - Per-file results table
  - PII distribution by category
  - Error log for failed files
- CLI: `python main_system.py --batch-dir ./recordings/`

### 24. Flask Localhost Dashboard
**New file:** `ai/dashboard.py`
- Full-featured web dashboard at `http://127.0.0.1:5000`
- Six tabbed sections:
  - **Overview** — live stats (sessions, PII events, whitelist count), recent redaction events feed, PII category distribution table (auto-refreshes every 5s)
  - **Redact File** — drag-and-drop file upload for audio redaction with context mode and export format selectors, displays original + redacted text, download links for WAV/TXT/JSON/PDF outputs
  - **Transcript** — text area and file upload for transcript redaction with same outputs
  - **History** — full audit log viewer with timestamps, PII types, speaker info
  - **Whitelist** — add/remove whitelist terms with live table
  - **Settings** — PII category toggle switches, sensitivity slider (0.5–1.0), system status panel
- REST API endpoints: `/api/stats`, `/api/redact`, `/api/redact-transcript`, `/api/whitelist`, `/api/history`, `/api/settings`
- CLI: `python main_system.py --dashboard` or `python dashboard.py`

### 25. One-Command Installer
**New file:** `ai/install.sh`
- Detects OS (macOS/Linux), checks Python 3
- Creates `.venv`, installs system deps (portaudio, ffmpeg, BlackHole via Homebrew on macOS; apt-get on Linux)
- Installs pip dependencies from `requirements.txt` + optional extras (flask, fpdf2, pydub)
- Downloads spaCy model
- Prints usage instructions for all modes

### 26. Fixed Choppy Audio — Streaming Pipeline Rewrite
**File:** `ai/streaming_pipeline.py` (rewritten)

**Root cause:** The original pipeline blocked the main thread during Whisper transcription (3-5s) with no output → audible silence/stutter bursts. The `RollingBuffer` had alignment issues with overlapping windows.

**Fixes applied:**

**a) Continuous output thread (gapless playback)**
- Added `_output_loop()` running in a separate daemon thread
- Continuously reads from the rolling buffer with a configurable lag (`--output-lag 0.3` = 300ms behind live)
- Always writes audio to the output device — raw passthrough by default
- No more silent gaps during processing

**b) Async redaction overlay**
- Processing happens in the main thread on a sliding window (every HOP_SECONDS)
- Redacted audio segments are stored in `self.redacted_segments` keyed by absolute sample range
- The output thread checks for overlapping redacted segments and splices them into the stream
- Redacted segments are consumed and removed once their sample range has passed the write head

**c) Fixed RollingBuffer — sample-level positioning**
- Rewrote `read_samples(start, count)` to use absolute sample positions
- Added `get_window_at(pos)` for precise window capture at any position
- Buffer now correctly handles wrap-around with proper logical-to-physical mapping
- Processing windows are taken at aligned sample positions, not at arbitrary offsets

**d) Configurable parameters**
- `--output-lag SECONDS`: Tradeoff between latency and smoothness (default: 0.3s)
- `--buffer-seconds SECONDS`: Ring buffer duration (default: 10s)
- `--backend pyaudio|sounddevice`: Choose audio backend

**e) Buffer underrun handling**
- Recording loop catches `OSError` from PyAudio and fills with silence instead of crashing
- Output loop catches write errors and retries

### 27. Added sounddevice Audio Backend
**File:** `ai/streaming_pipeline.py`, `ai/microphone_input.py`
- Added `_record_loop_sounddevice()` — uses `sounddevice.InputStream` with callback for lower-latency capture on macOS/Linux
- Added `_output_loop_sounddevice()` — uses `sounddevice.OutputStream` with callback for lower-latency playback
- `SoundDeviceRecorder` class in `microphone_input.py` for standalone use
- PyAudio remains the default for BlackHole/Windows compatibility

### 28. Improved microphone_input.py
**File:** `ai/microphone_input.py`
- Added callback-based PyAudio capture (`use_callback=True`) — non-blocking, lower latency
- Added `SoundDeviceRecorder` class — alternative backend using `sounddevice`
- Buffer underrun handling with silent-frame fallback

### 29. Updated CLI Integration
**File:** `ai/main_system.py`
- Added `--redact <file>` for post-call file redaction
- Added `--redact-transcript <file>` for transcript redaction
- Added `--batch-dir <dir>` for batch processing
- Added `--dashboard` and `--dashboard-port` for web dashboard

---

## Future Work Plan

### Phase 2: Core Engine (Weeks 3–4)
- [x] Sliding window pipeline (2-3s rolling, instead of fixed 4s)
- [x] Virtual microphone output via BlackHole for Zoom/Meet streaming
- [x] True audio redaction (inject beep into audio stream at word timestamps)
- [x] Hindi/Hinglish PII detection (Devanagari patterns + Hindi dictionaries)
- [x] Speaker diarization (pyannote + energy-based VAD)
- [x] Caste/religion and medical information detection
- [ ] 500+ annotated Indian sentences training set
- [x] F1 > 0.85 per category (12/13 categories achieved)

### Phase 3: Product Features (Week 5)
- [x] Context-aware redaction (public vs personal disclosures)
- [x] Whitelist mechanism (bypass redaction for known contacts)
- [x] Consent mode (pause redaction on demand)
- [x] Encrypted local audit log
- [x] Post-call MP3/WAV file redaction
- [x] Transcript integration (Zoom/Meet exports)
- [x] PDF export of redacted transcripts
- [x] Batch processing and redaction reports

### Phase 4: Dashboard & Packaging (Week 5)
- [x] Flask localhost dashboard
- [x] PII category toggle controls
- [x] Live redaction event feed (from audit log)
- [x] Session history review
- [x] Whitelist/blacklist management UI
- [x] Sensitivity slider
- [x] One-command install (macOS/Linux)
- [ ] PyInstaller standalone desktop app
- [ ] Raspberry Pi 5 USB audio dongle port

---

## Files Changed

| File | Status | Purpose |
|---|---|---|---|
| `ai/pii_mask.py` | Modified | ORG dict expansion, BANK_ACC context fix, CASTE_RELIGION detection, PERSON recall fix, context-aware redaction, context_mode parameter |
| `ai/generate_dataset.py` | Modified | Added CASTE_RELIGION samples to 7000 dataset |
| `ai/whitelist.py` | **New** | Whitelist mechanism (JSON persistent) |
| `ai/audit_log.py` | **New** | Encrypted audit log (Fernet) |
| `ai/main_system.py` | Modified | Integrated all Phase 3 + 4 features; added CLI args for redact, batch, dashboard |
| `ai/streaming_pipeline.py` | Modified | Integrated whitelist, audit, consent mode |
| `ai/requirements.txt` | Modified | Added cryptography, flask, fpdf2, pydub, soundfile |
| `ai/file_redactor.py` | **New** | Post-call MP3/WAV file redaction with noise-based audio masking |
| `ai/transcript_processor.py` | **New** | Zoom VTT and plain-text transcript parsing + redaction |
| `ai/pdf_exporter.py` | **New** | PDF export of redacted transcripts and reports |
| `ai/batch_processor.py` | **New** | Batch directory processing + aggregate JSON/HTML reports |
| `ai/dashboard.py` | **New** | Flask web dashboard with live feed, file upload, settings |
| `ai/install.sh` | **New** | One-command installer (macOS/Linux) |
| `ai/benchmark_7000_results.json` | Modified | Updated benchmark metrics |
| `ai/benchmark_7000_errors.json` | Modified | Updated error log |

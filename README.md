# NLP Project — IIT BHU: Privacy-Preserving Voice Assistant

A software privacy filter for your microphone that runs entirely on your laptop — no cloud, no internet needed. It sits between your microphone and the internet, transcribes audio locally, detects sensitive information (PII), and replaces those words with a beep before anything leaves your device.

```
Microphone → Whisper (Local STT) → PII Mask (spaCy + Regex) → Redacted Audio
```

---

## Project Structure

```
NLP-PROJECT-IIT-BHU/
├── ai/
│   ├── main_system.py           # Orchestrates record → transcribe → detect → beep
│   ├── microphone_input.py      # PyAudio live capture, WAV saving, level monitoring
│   ├── transcriber.py           # OpenAI Whisper (small) with word timestamps
│   ├── pii_mask.py              # spaCy NER + rule-based Indian PII detection
│   ├── streaming_pipeline.py    # Sliding-window streaming pipeline with BlackHole
│   ├── diarization.py           # Speaker diarization (pyannote)
│   ├── file_redactor.py         # Post-call WAV/MP3 file redaction
│   ├── transcript_processor.py  # Zoom/Meet VTT transcript parsing
│   ├── pdf_exporter.py          # PDF export of redacted transcripts
│   ├── batch_processor.py       # Directory-level batch processing
│   ├── dashboard.py             # Flask web dashboard
│   ├── echo_canceller.py        # NLMS acoustic echo cancellation
│   ├── whitelist.py             # Persistent whitelist mechanism
│   ├── audit_log.py             # Encrypted audit log (Fernet)
│   ├── benchmark.py             # Original 40-sample mini benchmark
│   ├── benchmark_7000.py        # 7000-sample benchmark pipeline
│   ├── generate_dataset.py      # 7000-sample Indian-context test data generator
│   ├── requirements.txt         # Python dependencies
│   ├── README.md                # AI module documentation
│   └── PROJECT_REPORT.md        # Detailed project report & benchmark results
│
├── .gitignore
└── README.md
```

---

## PII Detection Categories

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
| PERSON | spaCy NER (`en_core_web_sm`) | NER |
| ORG | spaCy NER | NER |
| GPE/LOC | spaCy NER | NER |

---

## Features

- Real-time microphone audio capture
- Local speech-to-text transcription (OpenAI Whisper)
- PII detection & masking (11 categories)
- Priority-based span merging for overlapping detections
- Audio beep redaction at word timestamps
- Sliding window streaming pipeline (2–3s rolling)
- BlackHole virtual microphone output for Zoom/Meet
- Speaker diarization (pyannote)
- 7000-sample benchmark suite with per-category metrics
- Modular and scalable architecture

---

## Technology Stack

- **Python 3.9+**
- **OpenAI Whisper** (local STT)
- **spaCy** (`en_core_web_sm`) for NER
- **PyAudio** for audio capture
- **pyannote** for speaker diarization
- **NumPy** for audio processing

---

## Setup

```bash
# Clone
git clone https://github.com/anubhav-kayal/NLP-PROJECT-IIT-BHU.git
cd NLP-PROJECT-IIT-BHU

# Python environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r ai/requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

---

## Usage

### Fixed-Record Mode (legacy)
```bash
cd ai/
python main_system.py --fixed
```

### Streaming Mode (with BlackHole)
```bash
cd ai/
python main_system.py --blackhole
```

### Phase 3 Features
```bash
# Context-aware redaction (only redact personal disclosures)
python main_system.py --context-mode personal

# Consent mode (toggle pause/resume with 'c' key)
python main_system.py --fixed --consent

# Whitelist management
python main_system.py --whitelist-add "Rahul"
python main_system.py --whitelist-remove "Rahul"
python main_system.py --whitelist-list

# Encrypted audit log
python main_system.py --fixed --audit
python main_system.py --view-audit

# Combine features
python main_system.py --blackhole --context-mode personal --consent --audit
```

### Run Benchmark
```bash
cd ai/
python benchmark_7000.py
```

### Generate Test Dataset
```bash
cd ai/
python generate_dataset.py
```

---

## Benchmark Results (7000 Samples)

| Metric | Before Fixes | After Fixes |
|---|---|---|
| Overall F1 | 0.644 | **0.687** |
| Precision | 0.654 | **0.713** |
| Recall | 0.634 | **0.663** |
| PHONE F1 | 0.374 | **0.896** |
| BANK_ACC FPs | 551 | **0** |
| ORG FPs | 1956 | **1469** |
| Error samples | 3295 (47.1%) | **2698** (38.5%) |

### Per-Category (After Fixes)

| Category | Precision | Recall | F1 |
|---|---|---|---|
| UPI_ID | 1.000 | 0.782 | **0.878** |
| PAN | 1.000 | 0.772 | **0.871** |
| EMAIL | 1.000 | 0.747 | **0.855** |
| PHONE | 1.000 | 0.812 | **0.896** |
| PINCODE | 1.000 | 0.677 | **0.808** |
| IFSC | 1.000 | 0.684 | **0.813** |
| AADHAAR | 0.610 | 0.787 | **0.687** |
| PERSON | 0.752 | 0.605 | **0.670** |
| GPE | 0.589 | 0.428 | **0.496** |
| ORG | 0.237 | 0.806 | **0.367** |
| BANK_ACC | 1.000 | 0.076 | **0.141** |

---

## Future Scope

- Desktop app (PyInstaller bundle + system tray icon, no terminal required)
- Language translator (real-time translation of redacted speech)
- Low-latency inference optimization
- Multilingual speech processing (beyond English/Hindi)
- 500+ annotated Indian sentences training set for fine-tuning
- Auto-updater (Sparkle on macOS, Squirrel on Windows)

---

## Contributors

- Anubhav Kayal
- Reshal Agarwal

---

## License

This project is intended for academic and research purposes under IIT BHU initiatives.

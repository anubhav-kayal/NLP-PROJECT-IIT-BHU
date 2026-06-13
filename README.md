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
│   ├── benchmark.py             # Original 40-sample mini benchmark
│   ├── benchmark_7000.py        # 7000-sample benchmark pipeline
│   ├── generate_dataset.py      # 7000-sample Indian-context test data generator
│   ├── requirements.txt         # Python dependencies
│   ├── README.md                # AI module documentation
│   └── PROJECT_REPORT.md        # Detailed project report & benchmark results
│
├── hardware/
│   ├── esp32_starter.cpp        # ESP32 microcontroller starter code
│   └── README.md                # Hardware module documentation
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

- Speaker diarization
- Streaming transcription
- Edge AI deployment
- Low-latency inference
- Real-time analytics dashboard
- Multilingual speech processing
- Context-aware redaction
- Encrypted local audit log
- Flask/FastAPI dashboard
- One-command installer

---

## Contributors

- Anubhav Kayal
- IIT BHU NLP Project Team

---

## License

This project is intended for academic and research purposes under IIT BHU initiatives.

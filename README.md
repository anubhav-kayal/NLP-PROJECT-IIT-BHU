# NLP Project - IIT BHU

This repository contains the implementation framework for the IIT BHU NLP Project, focused on real-time audio processing, speech transcription, and privacy-aware Natural Language Processing pipelines.

The project integrates microphone-based audio acquisition with transcription and Personally Identifiable Information (PII) masking modules using Python.

---

# Project Structure


NLP-PROJECT-IIT-BHU/
├── ai/
│   ├── main_system.py          # Main NLP orchestration pipeline
│   ├── microphone_input.py     # Real-time microphone capture
│   ├── pii_mask.py             # PII masking and privacy filtering
│   ├── transcriber.py          # Speech-to-text transcription
│   ├── requirements.txt        # Python dependencies
│   └── README.md               # AI module documentation
│
├── .gitignore
└── README.md
Project Objectives
Real-time microphone input processing
Speech-to-text transcription
Privacy-preserving NLP pipelines
PII detection and masking
Modular and scalable AI architecture
Technology Stack
Python 3.9+
Speech Recognition
Audio Processing Libraries
NLP-based Text Processing
Privacy Filtering Systems
Repository Setup
Clone the Repository
git clone https://github.com/anubhav-kayal/NLP-PROJECT-IIT-BHU.git
cd NLP-PROJECT-IIT-BHU
Python Environment Setup
Windows
python -m venv .venv
.venv\Scripts\activate
macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
Install Dependencies
pip install -r ai/requirements.txt
Running the Project
cd ai/
python main_system.py
Module Descriptions
main_system.py

Central orchestration module connecting all NLP and audio-processing components.

microphone_input.py

Handles live microphone input and audio streaming.

transcriber.py

Performs speech-to-text conversion from audio streams.

pii_mask.py

Detects and masks Personally Identifiable Information (PII) from transcribed text.

Features
Real-time audio capture
Speech transcription pipeline
NLP preprocessing
PII masking and privacy filtering
Modular architecture for scalability
Research-oriented NLP workflow
Future Scope
Speaker diarization
Streaming transcription
Edge AI deployment
Low-latency inference
Real-time analytics dashboard
Multilingual speech processing
Contributors
Anubhav Kayal
IIT BHU NLP Project Team
License

This project is intended for academic and research purposes under IIT BHU initiatives.

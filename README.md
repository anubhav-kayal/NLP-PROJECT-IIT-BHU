# VIT-MPMC-Project

This repository contains starter code for microprocessor and microcontroller projects, specifically focusing on ESP32 development and Python-based audio processing.

## Project Structure

```
VIT-MPMC-Project/
├── hardware/                   # ESP32 microcontroller starter code
│   ├── esp32_starter.cpp       # Main ESP32 program
│   └── README.md               # ESP32 setup and usage guide
│
└── ai/                         # Python microphone input starter code
    ├── microphone_input.py     # Main Python program
    ├── requirements.txt        # Python dependencies
    └── README.md               # Python setup and usage guide
```

## Quick Start

### Environment Setup

To start the Python environment, run the following commands to setup and activate the virtual environment.

On Windows: 

```bash
python -m venv .venv
.venv\Scripts\activate
```

On MacOS / Linux: 

```bash
python3 -m venv .venv
source .venv\bin\activate
```

To install the requirements in the Python virtual environment, using the following command:

```bash
pip install -r ai/requirements
```

### ESP32 Development

The ESP32 folder contains starter code for programming ESP32 microcontrollers with Arduino framework.

**What you'll need:**
- ESP32 development board
- USB cable
- Arduino IDE or PlatformIO

**Get started:**
```bash
cd hardware/
# Follow instructions in hardware/README.md
```

Features:
- Basic setup and loop structure
- Serial communication
- LED blinking example
- Chip information display

### Python Microphone Input

The Python microphone folder contains starter code for capturing and processing audio from a microphone.

**What you'll need:**
- Python 3.6+
- Microphone (built-in or external)

**Get started:**
```bash
cd ai/
pip install -r requirements.txt
python microphone_input.py
```

Features:
- Real-time audio capture
- Audio recording and saving to WAV files
- Audio level monitoring
- Device listing

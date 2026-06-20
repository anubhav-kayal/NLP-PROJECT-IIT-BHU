#!/usr/bin/env bash
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║  Privacy-Preserving Voice Assistant      ║"
echo "  ║  IIT BHU NLP Project                     ║"
echo "  ║  One-Command Installer                   ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

OS="$(uname -s)"

# --------------- Python ---------------
echo -e "${YELLOW}[1/5] Checking Python...${NC}"
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo -e "${RED}Python 3 not found. Please install Python 3.9+ from https://python.org${NC}"
    exit 1
fi
PY_VER=$($PY --version 2>&1 | grep -Eo '[0-9]+\.[0-9]+' | head -1)
echo "  Found Python $PY_VER"

# --------------- Virtual Environment ---------------
echo -e "${YELLOW}[2/5] Setting up virtual environment...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    $PY -m venv .venv
    echo "  Created .venv"
else
    echo "  .venv already exists"
fi

source .venv/bin/activate

# --------------- System Dependencies ---------------
echo -e "${YELLOW}[3/5] Checking system dependencies...${NC}"

if [ "$OS" = "Darwin" ]; then
    if ! command -v brew &>/dev/null; then
        echo -e "${YELLOW}  Homebrew not found. Installing...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    if ! brew list portaudio &>/dev/null 2>&1; then
        echo "  Installing portaudio..."
        brew install portaudio
    else
        echo "  portaudio found"
    fi

    if ! brew list ffmpeg &>/dev/null 2>&1; then
        echo "  Installing ffmpeg..."
        brew install ffmpeg
    else
        echo "  ffmpeg found"
    fi

    if ! brew list blackhole &>/dev/null 2>&1; then
        echo -e "${YELLOW}  BlackHole (virtual audio) not found. Install? [y/N]${NC}"
        read -r bh_choice
        if [ "$bh_choice" = "y" ] || [ "$bh_choice" = "Y" ]; then
            brew install blackhole-2ch
            echo -e "${GREEN}  BlackHole installed. You may need to restart audio apps.${NC}"
        fi
    else
        echo "  BlackHole found"
    fi

elif [ "$OS" = "Linux" ]; then
    echo "  Installing system packages (requires sudo)..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq portaudio19-dev python3-pyaudio ffmpeg build-essential python3-dev 2>/dev/null || true
fi

# --------------- Python Dependencies ---------------
echo -e "${YELLOW}[4/5] Installing Python dependencies...${NC}"
$PY -m pip install --upgrade pip -q
$PY -m pip install -r requirements.txt -q

echo "  Installing optional extras..."
$PY -m pip install flask fpdf2 pydub soundfile 2>/dev/null || true

# --------------- spaCy Model ---------------
echo -e "${YELLOW}[5/5] Downloading spaCy model...${NC}"
$PY -m spacy download en_core_web_sm 2>/dev/null || {
    echo -e "${YELLOW}  Trying en_core_web_md...${NC}"
    $PY -m spacy download en_core_web_md 2>/dev/null || {
        echo -e "${YELLOW}  Trying en_core_web_lg...${NC}"
        $PY -m spacy download en_core_web_lg 2>/dev/null || echo -e "${RED}  Failed to download spaCy model. Run: python3 -m spacy download en_core_web_sm${NC}"
    }
}

# --------------- Done ---------------
echo ""
echo -e "${GREEN}${BOLD}  ✅ Installation complete!${NC}"
echo ""
echo -e "  ${BOLD}Usage:${NC}"
echo "    cd ai/"
echo "    source .venv/bin/activate"
echo ""
echo "  ${BOLD}Fixed-Record Mode:${NC}"
echo "    python main_system.py --fixed"
echo ""
echo "  ${BOLD}Streaming Mode:${NC}"
echo "    python main_system.py --blackhole"
echo ""
echo "  ${BOLD}Dashboard:${NC}"
echo "    python dashboard.py"
echo "    → http://127.0.0.1:5000"
echo ""
echo "  ${BOLD}File Redaction:${NC}"
echo "    python main_system.py --redact recording.wav"
echo ""
echo "  ${BOLD}Batch Processing:${NC}"
echo "    python main_system.py --batch-dir ./recordings/"
echo ""
echo "  ${BOLD}Transcript Redaction:${NC}"
echo "    python main_system.py --redact-transcript meeting.vtt"
echo ""
echo -e "${CYAN}  Happy redacting! 🛡️${NC}"

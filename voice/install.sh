#!/usr/bin/env bash
# Install OmegA Voice dependencies
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=== OmegA Voice — Installing dependencies ==="

# System deps
sudo apt-get install -y portaudio19-dev python3-pyaudio python3-dev \
  libsndfile1 ffmpeg 2>/dev/null || true

# Python deps (venv to avoid PEP 668)
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel 2>&1
"$VENV_DIR/bin/pip" install sounddevice numpy scipy webrtcvad openwakeword requests pyaudio livekit 2>&1

echo ""
echo "=== Done. Run with: bash ~/OmegA-Architecture/voice/start.sh ==="

#!/usr/bin/env bash
# Install OmegA Voice dependencies
set -euo pipefail

echo "=== OmegA Voice — Installing dependencies ==="

# System deps
sudo apt-get install -y portaudio19-dev python3-pyaudio python3-dev \
  libsndfile1 ffmpeg 2>/dev/null || true

# Python deps
pip install sounddevice numpy scipy webrtcvad openwakeword requests pyaudio 2>&1

echo ""
echo "=== Done. Run with: bash ~/OmegA-Architecture/voice/start.sh ==="

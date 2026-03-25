#!/usr/bin/env bash
# Start OmegA Phylactery Terminal
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load env (for local gateway fallback if desired)
if [ -f "$HOME/.omega/one-true.env" ]; then
  set -a
  source "$HOME/.omega/one-true.env"
  set +a
fi

# Use local gateway if running, otherwise fall back to Vercel
if curl -sf http://localhost:8787/api/v1/health > /dev/null 2>&1; then
  echo "[OmegA Voice] Local gateway detected — routing through localhost:8787"
  # Override STT/TTS to still use Vercel (they're serverless), but ask goes local
  export OMEGA_VOICE_URL="https://omega-sovereign.vercel.app"
  export OMEGA_LOCAL_ASK="http://localhost:8787"
else
  echo "[OmegA Voice] Using Vercel endpoints"
  export OMEGA_VOICE_URL="https://omega-sovereign.vercel.app"
fi

python3 "$SCRIPT_DIR/omega_voice.py" "$@"

# OmegA Voice (Phylactery Terminal)

Minimal usage:

```bash
cd /home/mega/OMEGA_WORKSPACE/CANON/OmegA-Architecture/voice
./install.sh
./start.sh
```

If you want to run directly without the helper script:

```bash
python3 omega_voice.py
```

## Environment

The voice loop reads environment variables directly. `start.sh` will also load
`~/.omega/one-true.env` if it exists.

Required for LiveKit:
- `LIVEKIT_URL` (LiveKit ws/wss URL)
- `LIVEKIT_TOKEN` (static token) or `LIVEKIT_TOKEN_URL` (HTTP endpoint that returns a token)

Optional:
- `LIVEKIT_DISABLE=1` to skip LiveKit entirely
- `LIVEKIT_TOKEN_FIELD` JSON field to read from `LIVEKIT_TOKEN_URL` (default: `token`)
- `LIVEKIT_TOKEN_BEARER` bearer token used to call `LIVEKIT_TOKEN_URL`
- `OMEGA_VOICE_URL` base URL for `/api/stt`, `/api/tts`, `/api/ask` (default: Vercel app)
- `OMEGA_LOCAL_ASK` local gateway URL (routes `/api/ask` through local gateway)
- `OMEGA_API_BEARER_TOKEN` bearer token for local gateway
- `OMEGA_VOICE_SIMPLE=1` for compact logs
- `OMEGA_VOICE_GREETING=1` to speak a greeting on boot

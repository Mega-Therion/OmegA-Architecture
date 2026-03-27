#!/usr/bin/env python3
"""
OmegA Voice — Phylactery Terminal
────────────────────────────────────────────────────────────────
Starts in ACTIVE mode: listens immediately, no wake word needed.
After silence/response, drops to SLEEP mode.
Wake word "mega" (or "omega") brings it back to ACTIVE.

Architecture:
  Mic → VAD silence detection → WAV buffer
      → POST /api/stt  → transcript
      → POST /api/ask  → OmegA reply
      → POST /api/tts  → audio bytes
      → playback

  [Sleep mode] → openwakeword detects "mega" → back to ACTIVE
────────────────────────────────────────────────────────────────
"""

import os, sys, io, time, queue, struct, wave, tempfile, threading, asyncio
import numpy as np
import sounddevice as sd
import requests
import base64
import subprocess

# ── Config ────────────────────────────────────────────────────────────────────

OMEGA_BASE   = os.getenv("OMEGA_VOICE_URL", "https://omega-sovereign.vercel.app")
STT_URL      = f"{OMEGA_BASE}/api/stt"
TTS_URL      = f"{OMEGA_BASE}/api/tts"
SIMPLE_UI    = os.getenv("OMEGA_VOICE_SIMPLE", "1") == "1"
ENABLE_GREETING = os.getenv("OMEGA_VOICE_GREETING", "0") == "1"

# LiveKit (optional)
LIVEKIT_URL   = os.getenv("LIVEKIT_URL", "").strip()
LIVEKIT_TOKEN = os.getenv("LIVEKIT_TOKEN", "").strip()
LIVEKIT_TOKEN_URL = os.getenv("LIVEKIT_TOKEN_URL", "").strip()
LIVEKIT_TOKEN_FIELD = os.getenv("LIVEKIT_TOKEN_FIELD", "token").strip()
LIVEKIT_TOKEN_BEARER = os.getenv("LIVEKIT_TOKEN_BEARER", "").strip()
LIVEKIT_DISABLE = os.getenv("LIVEKIT_DISABLE", "0") == "1"

# If local gateway is running, use it for ask (richer memory, streaming capable)
_local_ask   = os.getenv("OMEGA_LOCAL_ASK")
if _local_ask:
    BEARER   = os.getenv("OMEGA_API_BEARER_TOKEN", "")
    ASK_URL  = f"{_local_ask}/api/v1/chat"
    ASK_LOCAL = True
else:
    ASK_URL   = f"{OMEGA_BASE}/api/ask"
    ASK_LOCAL = False

SAMPLE_RATE  = 16000
CHANNELS     = 1
CHUNK_MS     = 30          # VAD frame size in ms (10, 20, or 30)
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_MS / 1000)

# How many consecutive silent chunks before we consider speech done
SILENCE_CHUNKS_THRESHOLD = int(1200 / CHUNK_MS)   # ~1.2 seconds of silence
# How many speech chunks before we start recording (avoids noise triggers)
SPEECH_ONSET_THRESHOLD   = int(200 / CHUNK_MS)    # ~200ms of speech
# Idle timeout before dropping to sleep mode (ms of silence after last response)
SLEEP_TIMEOUT_S          = 30

WAKE_WORDS   = ["mega", "omega"]

# ── State ─────────────────────────────────────────────────────────────────────

class State:
    ACTIVE = "ACTIVE"
    SLEEP  = "SLEEP"

state      = State.ACTIVE
state_lock = threading.Lock()

livekit_room = None
livekit_thread = None
livekit_stop = threading.Event()

# ── Helpers ───────────────────────────────────────────────────────────────────

def print_status(msg, color="\033[96m"):
    if SIMPLE_UI:
        print(f"omega-voice: {msg}", flush=True)
        return
    reset = "\033[0m"
    print(f"{color}[OmegA Voice]{reset} {msg}", flush=True)

def play_audio_bytes(pcm_b64: str):
    """Decode base64 PCM audio from Gemini TTS and play it."""
    try:
        raw = base64.b64decode(pcm_b64)
        # Gemini TTS returns 24kHz mono 16-bit PCM
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(arr, samplerate=24000, blocking=True)
    except Exception as e:
        print_status(f"Playback error: {e}", "\033[91m")

def speak(text: str):
    """Call TTS endpoint and play the response."""
    try:
        r = requests.post(TTS_URL, json={"text": text}, timeout=20)
        r.raise_for_status()
        audio_b64 = r.json().get("audio")
        if audio_b64:
            play_audio_bytes(audio_b64)
        else:
            print_status(f"TTS returned no audio. Text was: {text}", "\033[93m")
    except Exception as e:
        print_status(f"TTS error: {e}", "\033[91m")

def transcribe(wav_bytes: bytes) -> str:
    """Send WAV bytes to STT endpoint, return transcript."""
    try:
        files = {"audio": ("audio.wav", wav_bytes, "audio/wav")}
        r = requests.post(STT_URL, files=files, timeout=30)
        r.raise_for_status()
        return r.json().get("text", "").strip()
    except Exception as e:
        print_status(f"STT error: {e}", "\033[91m")
        return ""

def ask_omega(text: str) -> str:
    """Send text to OmegA, return reply. Routes to local gateway if available."""
    try:
        if ASK_LOCAL:
            headers = {"Authorization": f"Bearer {BEARER}", "Content-Type": "application/json"}
            r = requests.post(ASK_URL, json={"user": "mega", "message": text},
                              headers=headers, timeout=30)
        else:
            r = requests.post(ASK_URL, json={"text": text}, timeout=30)
        r.raise_for_status()
        data = r.json()
        return (data.get("reply") or data.get("response") or "").strip()
    except Exception as e:
        print_status(f"Ask error: {e}", "\033[91m")
        return "I encountered an error reaching my neural link."

def frames_to_wav(frames: list, rate: int = SAMPLE_RATE) -> bytes:
    """Convert list of int16 numpy chunks to WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(rate)
        for chunk in frames:
            wf.writeframes(chunk.tobytes())
    return buf.getvalue()

# ── LiveKit (optional) ────────────────────────────────────────────────────────

def resolve_livekit_token() -> str:
    """Return a LiveKit token from env or fetch it from LIVEKIT_TOKEN_URL."""
    if LIVEKIT_TOKEN:
        return LIVEKIT_TOKEN
    if not LIVEKIT_TOKEN_URL:
        return ""
    try:
        headers = {}
        if LIVEKIT_TOKEN_BEARER:
            headers["Authorization"] = f"Bearer {LIVEKIT_TOKEN_BEARER}"
        r = requests.get(LIVEKIT_TOKEN_URL, headers=headers, timeout=10)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = r.json()
            token = payload.get(LIVEKIT_TOKEN_FIELD, "")
            return token.strip() if isinstance(token, str) else ""
        return r.text.strip()
    except Exception as e:
        print_status(f"LiveKit token fetch failed: {e}", "\033[93m")
        return ""

def start_livekit_client():
    """Optional LiveKit client wiring. Requires LIVEKIT_URL + LIVEKIT_TOKEN (or token URL)."""
    global livekit_thread
    if LIVEKIT_DISABLE:
        return
    token = resolve_livekit_token()
    if not LIVEKIT_URL or not token:
        return
    if livekit_thread is not None:
        return
    try:
        from livekit.rtc import Room
    except Exception as e:
        print_status(f"LiveKit import failed: {e}", "\033[93m")
        return

    async def _connect():
        global livekit_room
        room = Room()
        livekit_room = room

        @room.on("connection_state_changed")
        def _on_state(state):
            print_status(f"livekit state: {state}", "\033[90m")

        try:
            await room.connect(LIVEKIT_URL, token)
            print_status("livekit connected", "\033[90m")
            while not livekit_stop.is_set():
                await asyncio.sleep(0.5)
        except Exception as e:
            print_status(f"LiveKit connect error: {e}", "\033[93m")
        finally:
            try:
                await room.disconnect()
            except Exception:
                pass
            print_status("livekit disconnected", "\033[90m")

    def _runner():
        asyncio.run(_connect())

    livekit_thread = threading.Thread(target=_runner, name="livekit-client", daemon=True)
    livekit_thread.start()

def stop_livekit_client():
    livekit_stop.set()
    if livekit_thread is not None:
        livekit_thread.join(timeout=2.0)

# ── VAD ───────────────────────────────────────────────────────────────────────

try:
    import webrtcvad
    vad = webrtcvad.Vad(2)  # aggressiveness 0-3
    HAS_VAD = True
except ImportError:
    HAS_VAD = False
    print_status("webrtcvad not available — using energy-based VAD", "\033[93m")

def is_speech(chunk_int16: np.ndarray) -> bool:
    if HAS_VAD:
        try:
            raw = chunk_int16.tobytes()
            return vad.is_speech(raw, SAMPLE_RATE)
        except Exception:
            pass
    # Fallback: energy threshold
    rms = np.sqrt(np.mean(chunk_int16.astype(np.float32) ** 2))
    return rms > 300

# ── Wake word ─────────────────────────────────────────────────────────────────

try:
    from openwakeword.model import Model as OWWModel
    oww = OWWModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
    # Note: openwakeword doesn't have a "mega" model out of the box.
    # We use STT-based wake word detection as the primary method (see below).
    HAS_OWW = True
except Exception:
    HAS_OWW = False

def contains_wake_word(text: str) -> bool:
    t = text.lower().strip()
    return any(w in t for w in WAKE_WORDS)

# ── Main voice loop ───────────────────────────────────────────────────────────

def run_voice_loop():
    global state

    audio_queue: queue.Queue = queue.Queue()
    last_active_time = time.time()

    def audio_callback(indata, frames, time_info, status):
        audio_queue.put(indata.copy())

    start_livekit_client()
    print_status("ready", "\033[92m")
    print_status("listening", "\033[92m")
    if ENABLE_GREETING:
        speak("Phylactery Terminal online. I am OmegA. Speak your mind.")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16',
        blocksize=CHUNK_FRAMES,
        callback=audio_callback,
    ):
        speech_buffer   = []
        silent_count    = 0
        speech_count    = 0
        recording       = False

        while True:
            try:
                chunk = audio_queue.get(timeout=0.1)
            except queue.Empty:
                # Check sleep timeout
                with state_lock:
                    if state == State.ACTIVE:
                        if time.time() - last_active_time > SLEEP_TIMEOUT_S:
                            state = State.SLEEP
                            print_status("sleep", "\033[93m")
                continue

            chunk_int16 = chunk[:, 0] if chunk.ndim > 1 else chunk.flatten()
            chunk_int16 = chunk_int16.astype(np.int16)

            with state_lock:
                current_state = state

            speech = is_speech(chunk_int16)

            # ── SLEEP mode: detect wake word via periodic STT ─────────────
            if current_state == State.SLEEP:
                # Accumulate ~2s of audio then check via STT
                speech_buffer.append(chunk_int16)
                if len(speech_buffer) >= int(2000 / CHUNK_MS):
                    wav = frames_to_wav(speech_buffer)
                    speech_buffer = []
                    text = transcribe(wav)
                    if text and contains_wake_word(text):
                        with state_lock:
                            state = State.ACTIVE
                        last_active_time = time.time()
                        print_status("wake", "\033[92m")
                        if ENABLE_GREETING:
                            speak("I'm here. Go ahead.")
                continue

            # ── ACTIVE mode: full VAD + record + process ──────────────────
            if speech:
                speech_count += 1
                silent_count  = 0
                if speech_count >= SPEECH_ONSET_THRESHOLD:
                    recording = True
                if recording:
                    speech_buffer.append(chunk_int16)
            else:
                if recording:
                    silent_count += 1
                    speech_buffer.append(chunk_int16)  # include trailing silence for natural ends

                    if silent_count >= SILENCE_CHUNKS_THRESHOLD:
                        # End of utterance — process it
                        print_status("processing", "\033[96m")
                        wav = frames_to_wav(speech_buffer)
                        speech_buffer = []
                        recording     = False
                        speech_count  = 0
                        silent_count  = 0

                        text = transcribe(wav)
                        if not text:
                            print_status("no input", "\033[93m")
                            last_active_time = time.time()
                            continue

                        print_status(f"you: {text}", "\033[97m")
                        reply = ask_omega(text)
                        print_status(f"omega: {reply}", "\033[95m")
                        speak(reply)
                        last_active_time = time.time()
                else:
                    speech_count = max(0, speech_count - 1)

# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        run_voice_loop()
    except KeyboardInterrupt:
        print_status("Phylactery Terminal closed.", "\033[93m")
    finally:
        stop_livekit_client()

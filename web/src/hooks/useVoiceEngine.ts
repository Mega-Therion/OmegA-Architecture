'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getSpeechRecognitionConstructor,
  type SpeechRecognitionInstance,
  type SpeechRecognitionEventLike,
  type SpeechRecognitionErrorEventLike,
} from '@/lib/speechRecognition';

export type VoiceState = 'dormant' | 'listening' | 'thinking' | 'speaking' | 'followup';

export interface VoiceEngineOptions {
  onTranscript: (text: string) => void;
  onTTSStart?: () => void;
  onTTSEnd?: () => void;
  followUpWindowMs?: number;
  ttsUrl?: string;
  autoStart?: boolean;
  useWhisper?: boolean;
}

export interface VoiceEngineReturn {
  voiceState: VoiceState;
  interim: string;
  micLevel: number;
  ttsLevel: number;
  supported: boolean;
  toggle: () => void;
  speakText: (text: string) => Promise<void>;
  stopSpeaking: () => void;
  wakeUp: () => void;
}

const WAKE_WORDS = ['mega', 'omega'];
const FOLLOW_UP_MS = 25_000;
const MIN_SPEECH_CHARS = 3;
const SILENCE_COMMIT_MS = 1400;

// Shared helper: drive an audio level meter from an AnalyserNode
function startLevelTick(
  analyser: AnalyserNode,
  setLevel: (v: number) => void,
  animRef: React.MutableRefObject<number | null>,
) {
  const buf = new Uint8Array(analyser.frequencyBinCount);
  const tick = () => {
    analyser.getByteFrequencyData(buf);
    const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
    setLevel(Math.min(avg / 80, 1));
    animRef.current = requestAnimationFrame(tick);
  };
  tick();
}

export function useVoiceEngine({
  onTranscript,
  onTTSStart,
  onTTSEnd,
  followUpWindowMs = FOLLOW_UP_MS,
  ttsUrl = '/api/tts',
  autoStart = true,
  useWhisper = false,
}: VoiceEngineOptions): VoiceEngineReturn {
  const [voiceState, setVoiceState] = useState<VoiceState>('dormant');
  const [interim, setInterim] = useState('');
  const [micLevel, setMicLevel] = useState(0);
  const [ttsLevel, setTtsLevel] = useState(0);
  const [supported, setSupported] = useState(false);

  const stateRef = useRef<VoiceState>('dormant');
  const recogRef = useRef<SpeechRecognitionInstance | null>(null);
  const followUpTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const micAnimRef = useRef<number | null>(null);
  const ttsSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const ttsCtxRef = useRef<AudioContext | null>(null);
  const ttsAnimRef = useRef<number | null>(null);
  const mutedRef = useRef(false);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Whisper recording refs (only used when useWhisper=true)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Stale-closure avoidance: callbacks read stateRef instead of voiceState
  const setState = useCallback((s: VoiceState) => {
    stateRef.current = s;
    setVoiceState(s);
  }, []);

  // ── Shared AudioContext ────────────────────────────────────────────────────
  const getAudioCtx = useCallback(() => {
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new AudioContext();
    }
    return audioCtxRef.current;
  }, []);

  // ── Mic level analyzer ─────────────────────────────────────────────────────
  const startMicAnalyzer = useCallback(async () => {
    try {
      const ctx = getAudioCtx();
      if (!micStreamRef.current) {
        micStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      }
      analyserRef.current?.disconnect();
      const src = ctx.createMediaStreamSource(micStreamRef.current);
      analyserRef.current = ctx.createAnalyser();
      analyserRef.current.fftSize = 128;
      src.connect(analyserRef.current);
      startLevelTick(analyserRef.current, setMicLevel, micAnimRef);
    } catch { /* mic denied */ }
  }, [getAudioCtx]);

  const stopMicAnalyzer = useCallback(() => {
    if (micAnimRef.current) {
      cancelAnimationFrame(micAnimRef.current);
      micAnimRef.current = null;
      setMicLevel(0);
    }
  }, []);

  // ── Follow-up window ──────────────────────────────────────────────────────
  const clearFollowUp = useCallback(() => {
    if (followUpTimer.current) clearTimeout(followUpTimer.current);
  }, []);

  const enterFollowUp = useCallback(() => {
    setState('followup');
    clearFollowUp();
    followUpTimer.current = setTimeout(() => {
      if (stateRef.current === 'followup') setState('dormant');
    }, followUpWindowMs);
  }, [setState, clearFollowUp, followUpWindowMs]);

  // ── TTS playback ──────────────────────────────────────────────────────────
  const stopSpeaking = useCallback(() => {
    ttsSourceRef.current?.stop();
    ttsSourceRef.current = null;
    if (ttsAnimRef.current) {
      cancelAnimationFrame(ttsAnimRef.current);
      ttsAnimRef.current = null;
    }
    // Close the dedicated TTS AudioContext to prevent leaks
    if (ttsCtxRef.current) {
      ttsCtxRef.current.close().catch(() => {});
      ttsCtxRef.current = null;
    }
    setTtsLevel(0);
  }, []);

  const speakText = useCallback(async (text: string): Promise<void> => {
    if (!text?.trim()) { enterFollowUp(); return; }
    stopSpeaking();
    setState('speaking');
    onTTSStart?.();

    try {
      const res = await fetch(ttsUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 2000) }),
      });
      const data = await res.json();

      if (!data.audio) throw new Error('No audio returned');

      const raw = atob(data.audio);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);

      // Dedicated context for TTS — tracked in ttsCtxRef for cleanup
      const ctx = new AudioContext();
      ttsCtxRef.current = ctx;
      const buffer = await ctx.decodeAudioData(bytes.buffer);

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 128;

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(analyser);
      analyser.connect(ctx.destination);
      ttsSourceRef.current = src;

      startLevelTick(analyser, setTtsLevel, ttsAnimRef);

      src.start();
      src.onended = () => {
        if (ttsAnimRef.current) cancelAnimationFrame(ttsAnimRef.current);
        ttsAnimRef.current = null;
        setTtsLevel(0);
        ctx.close().catch(() => {});
        ttsCtxRef.current = null;
        onTTSEnd?.();
        enterFollowUp();
      };
    } catch (e) {
      console.warn('[VoiceEngine] TTS error:', e);
      onTTSEnd?.();
      enterFollowUp();
    }
  }, [ttsUrl, stopSpeaking, setState, enterFollowUp, onTTSStart, onTTSEnd]);

  // ── Speech recognition ────────────────────────────────────────────────────
  const stopRecognition = useCallback(() => {
    try { recogRef.current?.stop(); } catch { /* ignore */ }
  }, []);

  const startRecognition = useCallback(() => {
    const SR = getSpeechRecognitionConstructor();
    if (!SR) return;

    stopRecognition();

    const r = new SR();
    r.continuous = true;
    r.interimResults = true;
    r.lang = 'en-US';
    r.maxAlternatives = 1;
    recogRef.current = r;

    let finalBuffer = '';
    let silenceTimer: ReturnType<typeof setTimeout> | null = null;

    const resetSilence = () => {
      if (silenceTimer) clearTimeout(silenceTimer);
      silenceTimer = setTimeout(() => {
        if (finalBuffer.trim().length >= MIN_SPEECH_CHARS &&
            (stateRef.current === 'listening' || stateRef.current === 'followup')) {
          const text = finalBuffer.trim();
          finalBuffer = '';
          setInterim('');
          stopMicAnalyzer();
          setState('thinking');
          onTranscript(text);
        }
      }, SILENCE_COMMIT_MS);
    };

    r.onresult = (e: SpeechRecognitionEventLike) => {
      let interimText = '';
      let newFinal = '';

      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) newFinal += t + ' ';
        else interimText += t;
      }

      if (newFinal) {
        finalBuffer += newFinal;
        resetSilence();
      }

      setInterim((finalBuffer + interimText).trim());

      if (stateRef.current === 'dormant') {
        const all = (finalBuffer + interimText).toLowerCase();
        if (WAKE_WORDS.some(w => all.includes(w))) {
          finalBuffer = '';
          setInterim('');
          setState('listening');
          startMicAnalyzer();
        }
      }
    };

    r.onspeechstart = () => {
      if (stateRef.current === 'dormant') return;
      if (stateRef.current === 'followup') {
        clearFollowUp();
        setState('listening');
        startMicAnalyzer();
      }
    };

    r.onerror = (e: SpeechRecognitionErrorEventLike) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return;
      console.warn('[VoiceEngine] Recognition error:', e.error);
    };

    r.onend = () => {
      if (!mutedRef.current &&
          stateRef.current !== 'thinking' &&
          stateRef.current !== 'speaking') {
        restartTimerRef.current = setTimeout(() => {
          restartTimerRef.current = null;
          if (!mutedRef.current) startRecognition();
        }, 200);
      }
    };

    try { r.start(); } catch { /* already running */ }
  }, [stopRecognition, stopMicAnalyzer, setState, startMicAnalyzer, onTranscript, clearFollowUp]);

  // ── Whisper recording ─────────────────────────────────────────────────────
  const startWhisperRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunksRef.current = [];
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        audioChunksRef.current = [];
        if (blob.size < 1000) { setState('listening'); startWhisperRecording(); return; }

        setState('thinking');
        const form = new FormData();
        form.append('audio', blob, 'recording.webm');
        try {
          const res = await fetch('/api/stt', { method: 'POST', body: form });
          const data = await res.json();
          if (data.text?.trim()) {
            onTranscript(data.text.trim());
          } else {
            setState('listening');
            startWhisperRecording();
          }
        } catch {
          setState('listening');
          startWhisperRecording();
        }
      };

      recorder.start(100); // collect chunks every 100ms

      // Silence detection via analyser
      const ctx = getAudioCtx();
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 128;
      src.connect(analyser);
      analyserRef.current = analyser;
      startLevelTick(analyser, setMicLevel, micAnimRef);

      const buf = new Uint8Array(analyser.frequencyBinCount);
      const checkSilence = () => {
        analyser.getByteFrequencyData(buf);
        const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
        if (avg < 5) {
          if (!silenceTimerRef.current) {
            silenceTimerRef.current = setTimeout(() => {
              silenceTimerRef.current = null;
              if (mediaRecorderRef.current?.state === 'recording') {
                stopMicAnalyzer();
                mediaRecorderRef.current.stop();
              }
            }, 1500);
          }
        } else {
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
          }
        }
        if (stateRef.current === 'listening') requestAnimationFrame(checkSilence);
      };
      requestAnimationFrame(checkSilence);
    } catch (e) {
      console.warn('[VoiceEngine] Whisper recording failed:', e);
    }
  }, [getAudioCtx, onTranscript, setState, stopMicAnalyzer]);

  // ── Public controls ───────────────────────────────────────────────────────
  const wakeUp = useCallback(() => {
    clearFollowUp();
    setState('listening');
    startMicAnalyzer();
  }, [setState, clearFollowUp, startMicAnalyzer]);

  const toggle = useCallback(() => {
    if (stateRef.current === 'dormant') {
      mutedRef.current = false;
      if (useWhisper) {
        setState('listening');
        startWhisperRecording();
      } else {
        wakeUp();
        startRecognition();
      }
    } else {
      mutedRef.current = true;
      if (useWhisper) {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
        mediaRecorderRef.current = null;
      } else {
        stopRecognition();
      }
      stopSpeaking();
      stopMicAnalyzer();
      clearFollowUp();
      setState('dormant');
    }
  }, [useWhisper, wakeUp, startRecognition, startWhisperRecording, stopRecognition, stopSpeaking, stopMicAnalyzer, clearFollowUp, setState]);

  // ── Init ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    const hasSR = typeof window !== 'undefined' &&
      !!getSpeechRecognitionConstructor();
    setSupported(useWhisper ? true : hasSR);
    if (!autoStart) return;

    if (useWhisper) {
      const t = setTimeout(() => {
        mutedRef.current = false;
        setState('listening');
        startWhisperRecording();
      }, 800);
      return () => {
        clearTimeout(t);
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
        mutedRef.current = true;
        stopMicAnalyzer();
        clearFollowUp();
      };
    }

    if (!hasSR) return;

    const t = setTimeout(() => {
      mutedRef.current = false;
      startRecognition();
      setState('listening');
      startMicAnalyzer();
    }, 800);

    return () => {
      clearTimeout(t);
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      mutedRef.current = true;
      stopRecognition();
      stopMicAnalyzer();
      clearFollowUp();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Restart recognition whenever we enter listening or followup.
  // recogRef is never nulled after first start, so we can't use it as a
  // "is running" guard — always restart to ensure the mic is live.
  useEffect(() => {
    if (!useWhisper && (voiceState === 'listening' || voiceState === 'followup')) {
      startRecognition();
    }
  }, [useWhisper, voiceState, startRecognition]);

  return { voiceState, interim, micLevel, ttsLevel, supported, toggle, speakText, stopSpeaking, wakeUp };
}

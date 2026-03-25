'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export type VoiceState = 'dormant' | 'listening' | 'thinking' | 'speaking' | 'followup';

export interface VoiceEngineOptions {
  onTranscript: (text: string) => void;
  onTTSStart?: () => void;
  onTTSEnd?: () => void;
  followUpWindowMs?: number;
  ttsUrl?: string;
  autoStart?: boolean;
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

export function useVoiceEngine({
  onTranscript,
  onTTSStart,
  onTTSEnd,
  followUpWindowMs = FOLLOW_UP_MS,
  ttsUrl = '/api/tts',
  autoStart = true,
}: VoiceEngineOptions): VoiceEngineReturn {
  const [voiceState, setVoiceState] = useState<VoiceState>('dormant');
  const [interim, setInterim] = useState('');
  const [micLevel, setMicLevel] = useState(0);
  const [ttsLevel, setTtsLevel] = useState(0);
  const [supported, setSupported] = useState(false);

  const stateRef = useRef<VoiceState>('dormant');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recogRef = useRef<any>(null);
  const followUpTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const micAnimRef = useRef<number | null>(null);
  const ttsSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const ttsAnalyserRef = useRef<AnalyserNode | null>(null);
  const ttsAnimRef = useRef<number | null>(null);
  const mutedRef = useRef(false);

  // Keep stateRef in sync
  const setState = useCallback((s: VoiceState) => {
    stateRef.current = s;
    setVoiceState(s);
  }, []);

  // ── Mic level analyzer ─────────────────────────────────────────────────────
  const startMicAnalyzer = useCallback(async () => {
    try {
      if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
        audioCtxRef.current = new AudioContext();
      }
      if (!micStreamRef.current) {
        micStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      }
      const src = audioCtxRef.current.createMediaStreamSource(micStreamRef.current);
      analyserRef.current = audioCtxRef.current.createAnalyser();
      analyserRef.current.fftSize = 128;
      src.connect(analyserRef.current);

      const tick = () => {
        if (!analyserRef.current) return;
        const buf = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(buf);
        const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
        setMicLevel(Math.min(avg / 80, 1));
        micAnimRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch { /* mic denied — voice still works via recognition */ }
  }, []);

  const stopMicAnalyzer = useCallback(() => {
    if (micAnimRef.current) cancelAnimationFrame(micAnimRef.current);
    setMicLevel(0);
  }, []);

  // ── Follow-up window ────────────────────────────────────────────────────────
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

  // ── TTS playback ────────────────────────────────────────────────────────────
  const stopSpeaking = useCallback(() => {
    ttsSourceRef.current?.stop();
    ttsSourceRef.current = null;
    if (ttsAnimRef.current) cancelAnimationFrame(ttsAnimRef.current);
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

      // Decode base64 WAV
      const raw = atob(data.audio);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);

      const ctx = new AudioContext();
      const buffer = await ctx.decodeAudioData(bytes.buffer);

      // TTS level analyzer
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 128;
      ttsAnalyserRef.current = analyser;

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(analyser);
      analyser.connect(ctx.destination);
      ttsSourceRef.current = src;

      const tick = () => {
        if (!ttsAnalyserRef.current) return;
        const buf = new Uint8Array(ttsAnalyserRef.current.frequencyBinCount);
        ttsAnalyserRef.current.getByteFrequencyData(buf);
        const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
        setTtsLevel(Math.min(avg / 80, 1));
        ttsAnimRef.current = requestAnimationFrame(tick);
      };
      tick();

      src.start();
      src.onended = () => {
        if (ttsAnimRef.current) cancelAnimationFrame(ttsAnimRef.current);
        setTtsLevel(0);
        ctx.close();
        onTTSEnd?.();
        enterFollowUp();
      };
    } catch (e) {
      console.warn('[VoiceEngine] TTS error:', e);
      onTTSEnd?.();
      enterFollowUp();
    }
  }, [ttsUrl, stopSpeaking, setState, enterFollowUp, onTTSStart, onTTSEnd]);

  // ── Speech recognition ──────────────────────────────────────────────────────
  const stopRecognition = useCallback(() => {
    try { recogRef.current?.stop(); } catch { /* ignore */ }
  }, []);

  const startRecognition = useCallback(() => {
    const SR = (typeof window !== 'undefined')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ? ((window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition)
      : null;
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
      }, 1400);
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onresult = (e: any) => {
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

      // Wake word check when dormant
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

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onerror = (e: any) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return;
      console.warn('[VoiceEngine] Recognition error:', e.error);
    };

    r.onend = () => {
      // Auto-restart unless we're muted or thinking/speaking
      if (!mutedRef.current &&
          stateRef.current !== 'thinking' &&
          stateRef.current !== 'speaking') {
        setTimeout(() => { if (!mutedRef.current) startRecognition(); }, 200);
      }
    };

    try { r.start(); } catch { /* already running */ }
  }, [stopRecognition, stopMicAnalyzer, setState, startMicAnalyzer, onTranscript, clearFollowUp]);

  // ── Public controls ─────────────────────────────────────────────────────────
  const wakeUp = useCallback(() => {
    clearFollowUp();
    setState('listening');
    startMicAnalyzer();
  }, [setState, clearFollowUp, startMicAnalyzer]);

  const toggle = useCallback(() => {
    if (stateRef.current === 'dormant') {
      mutedRef.current = false;
      wakeUp();
      startRecognition();
    } else {
      mutedRef.current = true;
      stopRecognition();
      stopSpeaking();
      stopMicAnalyzer();
      clearFollowUp();
      setState('dormant');
    }
  }, [wakeUp, startRecognition, stopRecognition, stopSpeaking, stopMicAnalyzer, clearFollowUp, setState]);

  // ── Init ────────────────────────────────────────────────────────────────────
  useEffect(() => {
    const hasSR = typeof window !== 'undefined' &&
      !!((window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition);
    setSupported(hasSR);
    if (!hasSR || !autoStart) return;

    // Small delay to let the page settle
    const t = setTimeout(() => {
      mutedRef.current = false;
      startRecognition();
      // Start in listening mode immediately
      setState('listening');
      startMicAnalyzer();
    }, 800);

    return () => {
      clearTimeout(t);
      mutedRef.current = true;
      stopRecognition();
      stopMicAnalyzer();
      clearFollowUp();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When thinking ends (canvasState goes back to idle from parent), restart recognition
  useEffect(() => {
    if (voiceState === 'listening' || voiceState === 'followup') {
      if (!recogRef.current) startRecognition();
    }
  }, [voiceState, startRecognition]);

  return { voiceState, interim, micLevel, ttsLevel, supported, toggle, speakText, stopSpeaking, wakeUp };
}

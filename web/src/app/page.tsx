'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import s from './page.module.css';

// ── Types ──────────────────────────────────────────────────────────────────────

type VoiceState = 'offline' | 'monitoring' | 'awake' | 'thinking' | 'grounded';

interface HistoryMsg { role: 'user' | 'omega'; text: string; }

// ── PCM → WAV ──────────────────────────────────────────────────────────────────

function buildWav(base64: string): string {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const hdr = new ArrayBuffer(44);
  const v = new DataView(hdr);
  v.setUint32(0, 0x52494646, false); v.setUint32(4, 36 + bytes.length, true);
  v.setUint32(8, 0x57415645, false); v.setUint32(12, 0x666d7420, false);
  v.setUint16(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, 24000, true); v.setUint32(28, 48000, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  v.setUint32(36, 0x64617461, false); v.setUint32(40, bytes.length, true);
  const blob = new Blob([hdr, bytes], { type: 'audio/wav' });
  return URL.createObjectURL(blob);
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function Home() {
  const canvasRef       = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recogRef        = useRef<any>(null);
  const audioRef        = useRef<HTMLAudioElement | null>(null);
  const syncRef         = useRef<ReturnType<typeof setInterval> | null>(null);
  const historyRef      = useRef<HistoryMsg[]>([]);
  const rotSpeedRef     = useRef(0.0004);
  const pointsRef       = useRef<any>(null);
  const stateRef        = useRef<VoiceState>('offline');

  const [started,        setStarted]        = useState(false);
  const [voiceState,     setVoiceState]      = useState<VoiceState>('offline');
  const [statusText,     setStatusText]      = useState('System Offline');
  const [words,          setWords]           = useState<{ text: string; cls: string }[]>([{ text: 'Awaiting voice command...', cls: s.wordActive }]);
  const [ripple,         setRipple]          = useState(false);
  const [showDistill,    setShowDistill]     = useState(false);
  const [showTheme,      setShowTheme]       = useState(false);
  const [manifestBg,     setManifestBg]      = useState('');
  const [manifestVis,    setManifestVis]     = useState(false);
  const [projection,     setProjection]      = useState('');
  const [projectionVis,  setProjectionVis]   = useState(false);
  const [canvasOpacity,  setCanvasOpacity]   = useState(0.3);

  // keep stateRef in sync
  const setState = useCallback((st: VoiceState) => {
    stateRef.current = st;
    setVoiceState(st);
  }, []);

  // ── Three.js particle field ──────────────────────────────────────────────────
  useEffect(() => {
    if (!started || !canvasRef.current) return;
    let animId: number;

    import('three').then(THREE => {
      const scene    = new THREE.Scene();
      const camera   = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setSize(window.innerWidth, window.innerHeight);
      canvasRef.current!.appendChild(renderer.domElement);

      const geo = new THREE.BufferGeometry();
      const pos = new Float32Array(1500 * 3);
      for (let i = 0; i < 4500; i++) pos[i] = (Math.random() - 0.5) * 12;
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      const mat = new THREE.PointsMaterial({ color: 0x555555, size: 0.015 });
      const pts = new THREE.Points(geo, mat);
      pointsRef.current = pts;
      scene.add(pts);
      camera.position.z = 5;

      const tick = () => {
        animId = requestAnimationFrame(tick);
        pts.rotation.y += rotSpeedRef.current;
        renderer.render(scene, camera);
      };
      tick();

      const onResize = () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      };
      window.addEventListener('resize', onResize);
      return () => {
        cancelAnimationFrame(animId);
        window.removeEventListener('resize', onResize);
        renderer.dispose();
      };
    });

    return () => cancelAnimationFrame(animId);
  }, [started]);

  // ── Speech recognition ───────────────────────────────────────────────────────
  const initSpeech = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = (window as any).webkitSpeechRecognition ?? (window as any).SpeechRecognition;
    if (!SR) { setStatusText('API Unsupported'); return; }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const r = new SR() as any;
    r.continuous = true;
    r.interimResults = true;
    r.lang = 'en-US';
    recogRef.current = r;

    r.onstart = () => {
      if (stateRef.current === 'offline') {
        setState('monitoring');
        setStatusText('Monitoring...');
      }
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onresult = (event: any) => {
      let interim = '', final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) final += event.results[i][0].transcript;
        else interim += event.results[i][0].transcript;
      }
      const full = (interim + final).toLowerCase();

      if (stateRef.current === 'monitoring') {
        if (['hey omega', 'mega', 'hey mega'].some(w => full.includes(w))) {
          wakeUp();
          return;
        }
      }
      if (stateRef.current === 'awake' && audioRef.current && !audioRef.current.paused && interim.trim().length > 2) {
        stopSpeaking();
        setStatusText('Listening...');
      }
      if (stateRef.current === 'awake' && final.trim().length > 0) {
        handleInput(final.trim());
      }
    };

    r.onerror = () => {};
    r.onend = () => { setTimeout(() => { try { r.start(); } catch (_) {} }, 100); };
    try { r.start(); } catch (_) {}
  }, [setState]);

  // ── Wake ─────────────────────────────────────────────────────────────────────
  const wakeUp = useCallback(() => {
    setState('awake');
    setStatusText('Neural Link Active');
    setRipple(true);
    setWords([{ text: 'I am here.', cls: s.wordActive }]);
  }, [setState]);

  // ── Stop speaking ─────────────────────────────────────────────────────────────
  const stopSpeaking = useCallback(() => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    if (syncRef.current) { clearInterval(syncRef.current); syncRef.current = null; }
  }, []);

  // ── Speak via /api/tts ────────────────────────────────────────────────────────
  const speak = useCallback(async (text: string) => {
    stopSpeaking();
    const clean = text.replace(/\*/g, '');
    const ws = clean.split(' ').map(w => ({ text: w, cls: s.word }));
    setWords(ws);

    try {
      const res  = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
      const data = await res.json();
      if (!data.audio) return;

      const url  = buildWav(data.audio);
      const audio = new Audio(url);
      audioRef.current = audio;

      await new Promise<void>(resolve => {
        audio.onloadedmetadata = () => {
          audio.play();
          resolve();
        };
      });

      const delay = (audio.duration * 1000) / ws.length;
      let idx = 0;
      syncRef.current = setInterval(() => {
        if (idx < ws.length) {
          setWords(prev => prev.map((w, i) =>
            i === idx ? { ...w, cls: `${s.word} ${s.wordActive}` } :
            i < idx   ? { ...w, cls: `${s.word} ${s.wordFaded}` } : w
          ));
          idx++;
        } else {
          if (syncRef.current) clearInterval(syncRef.current);
        }
      }, delay);
    } catch (_) {}
  }, [stopSpeaking]);

  // ── Apply resonance to visuals ────────────────────────────────────────────────
  const applyResonance = useCallback((mood: string) => {
    const map: Record<string, { speed: number; opacity: number }> = {
      CALM:      { speed: 0.0004, opacity: 0.2 },
      ENERGETIC: { speed: 0.005,  opacity: 0.5 },
      MELANCHOLY:{ speed: 0.0001, opacity: 0.1 },
      TENSE:     { speed: 0.015,  opacity: 0.4 },
    };
    const cfg = map[mood.toUpperCase()] ?? map.CALM;
    rotSpeedRef.current = cfg.speed;
    setCanvasOpacity(cfg.opacity);
  }, []);

  // ── Main input handler → /api/chat ────────────────────────────────────────────
  const handleInput = useCallback(async (text: string) => {
    setState('thinking');
    setStatusText('Processing...');
    historyRef.current.push({ role: 'user', text });
    if (historyRef.current.length > 2) { setShowDistill(true); setShowTheme(true); }

    try {
      // Quick resonance check
      const moodWords = text.toLowerCase();
      if (/urgent|critical|alert|danger/.test(moodWords)) applyResonance('TENSE');
      else if (/calm|peace|relax|quiet/.test(moodWords)) applyResonance('CALM');
      else if (/excit|amazing|great|awesome/.test(moodWords)) applyResonance('ENERGETIC');
      else if (/sad|miss|lost|alone/.test(moodWords)) applyResonance('MELANCHOLY');

      // Stream from /api/chat
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: text, history: historyRef.current.slice(0, -1), voiceMode: true }),
      });

      let reply = '';
      const reader = res.body!.getReader();
      const dec    = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = dec.decode(value, { stream: true });
        // Strip SSE status lines
        if (chunk.startsWith('data: {"type":"status"')) continue;
        reply += chunk;
      }
      reply = reply.trim();
      if (!reply || reply.toUpperCase().includes('IGNORE')) {
        setState('awake');
        setStatusText('Awaiting Input...');
        return;
      }

      historyRef.current.push({ role: 'omega', text: reply });
      setState('awake');
      setStatusText('Awaiting Input...');
      await speak(reply);
    } catch (_) {
      setState('awake');
      setStatusText('Signal Interference');
    }
  }, [setState, applyResonance, speak]);

  // ── Distill session ───────────────────────────────────────────────────────────
  const distillSession = useCallback(async () => {
    if (!historyRef.current.length) return;
    setStatusText('Distilling Essence...');
    const summary = historyRef.current.map(m => `${m.role}: ${m.text}`).join('\n');
    await handleInput(`Provide a 2-sentence poetic analysis of our conversation so far:\n${summary}`);
  }, [handleInput]);

  // ── Sync atmosphere ───────────────────────────────────────────────────────────
  const syncAtmosphere = useCallback(() => {
    const moods = ['CALM', 'ENERGETIC', 'MELANCHOLY', 'TENSE'];
    const recent = historyRef.current.slice(-4).map(m => m.text).join(' ').toLowerCase();
    if (/calm|peace|slow/.test(recent)) applyResonance('CALM');
    else if (/fast|excit|energy/.test(recent)) applyResonance('ENERGETIC');
    else if (/sad|lost|dark/.test(recent)) applyResonance('MELANCHOLY');
    else applyResonance(moods[Math.floor(Math.random() * moods.length)]);
  }, [applyResonance]);

  // ── Cognitive projection ──────────────────────────────────────────────────────
  const projectThought = useCallback(async () => {
    if (!historyRef.current.length) return;
    setProjection('Analyzing neural patterns...');
    setProjectionVis(true);
    const prompt = `Based on: "${historyRef.current.slice(-2).map(m => m.text).join(' ')}" — predict my next thought in 5 words or less.`;
    await handleInput(prompt);
    setTimeout(() => setProjectionVis(false), 5000);
  }, [handleInput]);

  // ── Core click ────────────────────────────────────────────────────────────────
  const handleCoreClick = useCallback(() => {
    if (voiceState === 'monitoring' || voiceState === 'offline') wakeUp();
    else projectThought();
  }, [voiceState, wakeUp, projectThought]);

  // ── Start system ─────────────────────────────────────────────────────────────
  const startSystem = useCallback(() => {
    setStarted(true);
    initSpeech();
  }, [initSpeech]);

  // ── Derived CSS classes ───────────────────────────────────────────────────────
  const coreClass  = [s.core,  voiceState === 'awake' || voiceState === 'thinking' ? s.coreActive : voiceState === 'grounded' ? s.coreGrounded : ''].join(' ');
  const badgeClass = [s.badge, voiceState === 'awake' || voiceState === 'thinking' ? s.badgeActive : voiceState === 'grounded' ? s.badgeGrounded : ''].join(' ');

  return (
    <div className={s.root}>
      {!started && (
        <div className={s.startOverlay} onClick={startSystem}>
          <span className={s.startLabel}>Initialize Neural Link</span>
        </div>
      )}

      <div className={s.canvasContainer} ref={canvasRef} style={{ opacity: canvasOpacity }} />

      {/* Manifestation frame */}
      <div
        className={`${s.manifestation} ${manifestVis ? s.manifestationVisible : ''}`}
        style={manifestBg ? { backgroundImage: `url(${manifestBg})` } : {}}
      />

      <span className={s.voiceIndicator}>VOICE: CHARON</span>
      <Link href="/tranquility" className={s.navLink}>TRANQUILITY</Link>

      <div className={s.layer}>
        <div className={s.statusWrap}>
          <span className={badgeClass}>{statusText}</span>
          <div className={s.featurePill}>
            RESONANCE · VISION MANIFEST · INSIGHT<br />
            QUANTUM GROUNDING · ATMOSPHERE · COGNITIVE PROJECTION
          </div>
        </div>

        <div className={coreClass} onClick={handleCoreClick}>
          <div className={`${s.projection} ${projectionVis ? s.projectionVisible : ''}`}>
            {projection}
          </div>
          <div className={`${s.ripple} ${ripple ? s.rippleAnimate : ''}`} />
          <div className={s.coreDot} />
        </div>

        <div className={s.transcript}>
          {words.map((w, i) => (
            <span key={i} className={w.cls}>{w.text} </span>
          ))}
        </div>
      </div>

      {showTheme && (
        <button className={`${s.floatingBtn} ${s.btnLeft}`} onClick={syncAtmosphere}>
          ✦ Sync Atmosphere
        </button>
      )}
      {showDistill && (
        <button className={`${s.floatingBtn} ${s.btnRight}`} onClick={distillSession}>
          ✦ Distill Session
        </button>
      )}
    </div>
  );
}

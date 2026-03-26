'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import s from './page.module.css';
import { useVoiceEngine, type VoiceEngineReturn } from '@/hooks/useVoiceEngine';

// ── Types ──────────────────────────────────────────────────────────────────────

interface HistoryMsg { role: 'user' | 'omega'; text: string; }

interface RotatingPoints {
  rotation: { y: number };
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function Home() {
  const canvasRef       = useRef<HTMLDivElement>(null);
  const historyRef      = useRef<HistoryMsg[]>([]);
  const rotSpeedRef     = useRef(0.0004);
  const pointsRef       = useRef<RotatingPoints | null>(null);
  const voiceRef        = useRef<VoiceEngineReturn | null>(null);

  const [started,        setStarted]        = useState(false);
  const [statusText,     setStatusText]     = useState('System Offline');
  const [words,          setWords]          = useState<{ text: string; cls: string }[]>([{ text: 'Awaiting voice command...', cls: s.wordActive }]);
  const [ripple,         setRipple]         = useState(false);
  const [canvasOpacity,  setCanvasOpacity]  = useState(0.3);
  const isStreamingRef = useRef(false);

  // ── Resonance ──────────────────────────────────────────────────────────────
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

  // ── Chat handler (streams text progressively) ──────────────────────────────
  const handleTranscript = useCallback(async (text: string) => {
    setStatusText('Processing...');
    historyRef.current.push({ role: 'user', text });

    // Quick resonance
    const lc = text.toLowerCase();
    if (/urgent|critical|alert|danger/.test(lc)) applyResonance('TENSE');
    else if (/calm|peace|relax|quiet/.test(lc)) applyResonance('CALM');
    else if (/excit|amazing|great|awesome/.test(lc)) applyResonance('ENERGETIC');
    else if (/sad|miss|lost|alone/.test(lc)) applyResonance('MELANCHOLY');

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: text, history: historyRef.current.slice(0, -1), voiceMode: true }),
      });

      const reader = res.body!.getReader();
      const dec = new TextDecoder();
      let fullReply = '';
      isStreamingRef.current = true;

      // Progressive word display as chunks arrive from LLM
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = dec.decode(value, { stream: true });

        // Skip SSE status lines
        if (chunk.startsWith('data: {"type":"status"')) continue;

        fullReply += chunk;

        // Update words progressively — latest words glow, older ones fade
        const cleanText = fullReply.replace(/\*/g, '');
        const wordList = cleanText.split(/\s+/).filter(w => w.length > 0);
        setWords(wordList.map((w, i) => ({
          text: w,
          cls: i >= wordList.length - 4 ? `${s.word} ${s.wordActive}` : `${s.word} ${s.wordFaded}`,
        })));
      }

      isStreamingRef.current = false;
      fullReply = fullReply.trim();

      if (!fullReply || fullReply.toUpperCase().includes('IGNORE')) {
        setStatusText('Awaiting Input...');
        return;
      }

      historyRef.current.push({ role: 'omega', text: fullReply });

      // All words fully visible after stream completes
      const finalWords = fullReply.replace(/\*/g, '').split(/\s+/).filter(w => w.length > 0);
      setWords(finalWords.map(w => ({ text: w, cls: `${s.word} ${s.wordActive}` })));

      // TTS — speak the full response
      setStatusText('Speaking...');
      await voiceRef.current?.speakText(fullReply);
      setStatusText('Awaiting Input...');
    } catch {
      setStatusText('Signal Interference');
    }
  }, [applyResonance]);

  // ── Voice engine hook ──────────────────────────────────────────────────────
  const voice = useVoiceEngine({
    onTranscript: handleTranscript,
    onTTSStart: () => setStatusText('Speaking...'),
    onTTSEnd: () => setStatusText('Awaiting Input...'),
    autoStart: false,
  });

  // Keep ref in sync so handleTranscript can call speakText
  voiceRef.current = voice;

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

  // ── Wake up ────────────────────────────────────────────────────────────────
  const handleWakeUp = useCallback(() => {
    voice.wakeUp();
    setRipple(true);
    setStatusText('Neural Link Active');
    setWords([{ text: 'I am here.', cls: s.wordActive }]);
  }, [voice]);

  // ── Core click ─────────────────────────────────────────────────────────────
  const handleCoreClick = useCallback(() => {
    if (voice.voiceState === 'dormant') handleWakeUp();
  }, [voice.voiceState, handleWakeUp]);

  // ── Start system ───────────────────────────────────────────────────────────
  function startSystem() {
    setStarted(true);
    setTimeout(() => {
      voice.toggle();
      setStatusText('Monitoring...');
    }, 500);
  }

  // ── Status text from voice state ───────────────────────────────────────────
  useEffect(() => {
    if (!started || isStreamingRef.current) return;
    switch (voice.voiceState) {
      case 'dormant':   setStatusText('Monitoring...'); break;
      case 'listening': setStatusText('Listening...'); break;
      case 'thinking':  setStatusText('Processing...'); break;
      case 'speaking':  setStatusText('Speaking...'); break;
      case 'followup':  setStatusText('Awaiting Input...'); break;
    }
  }, [voice.voiceState, started]);

  // ── Derived CSS classes ─────────────────────────────────────────────────────
  const isActive = voice.voiceState !== 'dormant';
  const coreClass  = [s.core, isActive ? s.coreActive : ''].join(' ');
  const badgeClass = [s.badge, isActive ? s.badgeActive : ''].join(' ');

  return (
    <div className={s.root}>
      {!started && (
        <div className={s.startOverlay} onClick={startSystem}>
          <span className={s.startLabel}>Initialize Neural Link</span>
        </div>
      )}

      <div className={s.canvasContainer} ref={canvasRef} style={{ opacity: canvasOpacity }} />

      <span className={s.voiceIndicator}>VOICE: CHARON</span>
      <Link href="/tranquility" className={s.navLink}>TRANQUILITY</Link>

      <div className={s.layer}>
        <div className={s.statusWrap}>
          <span className={badgeClass}>{statusText}</span>
          {voice.interim && (
            <div className={s.featurePill} style={{ opacity: 0.8, fontSize: '11px' }}>
              {voice.interim}
            </div>
          )}
        </div>

        <div className={coreClass} onClick={handleCoreClick}>
          <div className={`${s.ripple} ${ripple ? s.rippleAnimate : ''}`} />
          <div className={s.coreDot} style={{
            transform: `scale(${1 + voice.micLevel * 3 + voice.ttsLevel * 2})`,
            transition: 'transform 0.1s ease',
          }} />
        </div>

        <div className={s.transcript}>
          {words.map((w, i) => (
            <span key={i} className={w.cls}>{w.text} </span>
          ))}
        </div>
      </div>
    </div>
  );
}

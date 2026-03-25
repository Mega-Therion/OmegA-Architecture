'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import Link from 'next/link';
import s from './page.module.css';

// ── Types ──────────────────────────────────────────────────────────────────────

type VoiceState = 'dormant' | 'listening' | 'thinking' | 'speaking';

// ── Particle field ─────────────────────────────────────────────────────────────

function initParticles(canvas: HTMLCanvasElement, getState: () => VoiceState) {
  const ctx = canvas.getContext('2d')!;
  const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; };
  resize();
  window.addEventListener('resize', resize);

  const COUNT = 220;
  const particles = Array.from({ length: COUNT }, () => ({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    vx: (Math.random() - 0.5) * 0.18,
    vy: (Math.random() - 0.5) * 0.18,
    r: Math.random() * 1.2 + 0.3,
    opacity: Math.random() * 0.4 + 0.1,
  }));

  const COLORS: Record<VoiceState, string> = {
    dormant:   '139, 92, 246',
    listening: '228, 184, 74',
    thinking:  '196, 181, 253',
    speaking:  '196, 181, 253',
  };

  let raf: number;
  const draw = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const state = getState();
    const speed = state === 'thinking' ? 2.2 : state === 'speaking' ? 1.4 : 1;
    const color = COLORS[state];

    for (const p of particles) {
      p.x += p.vx * speed;
      p.y += p.vy * speed;
      if (p.x < 0) p.x = canvas.width;
      if (p.x > canvas.width) p.x = 0;
      if (p.y < 0) p.y = canvas.height;
      if (p.y > canvas.height) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color}, ${p.opacity})`;
      ctx.fill();
    }

    // Subtle connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 90) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(${color}, ${0.06 * (1 - dist / 90)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    raf = requestAnimationFrame(draw);
  };
  draw();
  return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
}

// ── Typewriter ─────────────────────────────────────────────────────────────────

function useTypewriter() {
  const [text, setText] = useState('');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const type = useCallback((full: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setText('');
    let i = 0;
    const tick = () => {
      if (i < full.length) {
        setText(full.slice(0, i + 1));
        i++;
        timerRef.current = setTimeout(tick, 28);
      }
    };
    tick();
  }, []);

  return { text, type };
}

// ── PCM → WAV player ───────────────────────────────────────────────────────────

function playPCM(base64: string) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const hdr = new ArrayBuffer(44);
  const v = new DataView(hdr);
  const sr = 24000;
  v.setUint32(0, 0x52494646, false); v.setUint32(4, 36 + bytes.length, true);
  v.setUint32(8, 0x57415645, false); v.setUint32(12, 0x666d7420, false);
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  v.setUint32(36, 0x64617461, false); v.setUint32(40, bytes.length, true);
  const blob = new Blob([hdr, bytes], { type: 'audio/wav' });
  return new Audio(URL.createObjectURL(blob));
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function Tranquility() {
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const stateRef   = useRef<VoiceState>('dormant');
  const recogRef   = useRef<SpeechRecognition | null>(null);
  const audioRef   = useRef<HTMLAudioElement | null>(null);

  const [voiceState, setVoiceState]         = useState<VoiceState>('dormant');
  const [userLine, setUserLine]             = useState('Speak when you are ready...');
  const [manifest, setManifest]             = useState<string | null>(null);
  const [seed, setSeed]                     = useState<string | null>(null);
  const [lastExchange, setLastExchange]     = useState({ user: '', omega: '' });

  const { text: omegaText, type: typeOmega } = useTypewriter();

  const setState = useCallback((st: VoiceState) => {
    stateRef.current = st;
    setVoiceState(st);
  }, []);

  // ── Particle canvas ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!canvasRef.current) return;
    return initParticles(canvasRef.current, () => stateRef.current);
  }, []);

  // ── TTS via /api/tts ─────────────────────────────────────────────────────────
  const speakText = useCallback(async (text: string) => {
    setState('speaking');
    typeOmega(text);
    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 2000) }),
      });
      const data = await res.json();
      if (data.audio) {
        audioRef.current?.pause();
        const audio = playPCM(data.audio);
        audioRef.current = audio;
        audio.play();
        audio.onended = () => setState('dormant');
      } else {
        setState('dormant');
      }
    } catch {
      setState('dormant');
    }
  }, [setState, typeOmega]);

  // ── Chat via /api/chat (voiceMode) ───────────────────────────────────────────
  const processInput = useCallback(async (text: string) => {
    setState('thinking');
    typeOmega('...');
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: text, voiceMode: true }),
      });

      const hasVisual = res.headers.get('x-has-visual') === 'true';
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let reply = '';
      if (reader) {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          // Strip SSE status lines
          const text = chunk.replace(/data: \{.*?\}\n\n/g, '');
          reply += text;
        }
      }

      const cleanReply = reply.replace(/\[VISUAL_READY\]/g, '').trim();
      const wantsVisual = reply.includes('[VISUAL_READY]') || hasVisual;

      setLastExchange({ user: text, omega: cleanReply });
      await speakText(cleanReply);

      if (wantsVisual) {
        await generateManifestation(text, cleanReply);
      }
    } catch {
      typeOmega('A moment of silence.');
      setState('dormant');
    }
  }, [setState, speakText, typeOmega]);

  // ── Speech recognition ───────────────────────────────────────────────────────
  const startListening = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const r = new SR() as SpeechRecognition;
    r.continuous = false;
    r.interimResults = true;
    r.lang = 'en-US';
    recogRef.current = r;

    r.onstart = () => setState('listening');
    r.onresult = (e) => {
      let t = '';
      for (let i = e.resultIndex; i < e.results.length; i++) t += e.results[i][0].transcript;
      setUserLine(`"${t}"`);
      if (e.results[e.results.length - 1].isFinal) {
        r.stop();
        processInput(t);
      }
    };
    r.onend = () => { if (stateRef.current === 'listening') setState('dormant'); };
    r.start();
  }, [setState, processInput]);

  const toggleListening = useCallback(() => {
    if (voiceState === 'listening') {
      recogRef.current?.stop();
      setState('dormant');
    } else if (voiceState === 'dormant') {
      setUserLine('Presence felt...');
      startListening();
    }
  }, [voiceState, setState, startListening]);

  // ── Ethereal Resonance ───────────────────────────────────────────────────────
  const etherealResonance = useCallback(async () => {
    if (!lastExchange.user) return;
    const prompt = `Distill the emotional and philosophical current of this exchange into exactly three words and a hex color that embodies the mood. Format as JSON: {"color":"#hex","vibe":"word word word"}
User: "${lastExchange.user}"
OmegA: "${lastExchange.omega}"`;
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: prompt, voiceMode: false }),
      });
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let raw = '';
      if (reader) {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          raw += decoder.decode(value, { stream: true });
        }
      }
      const jsonStr = raw.match(/\{[^}]+\}/)?.[0] ?? '';
      if (jsonStr) {
        const data = JSON.parse(jsonStr);
        setManifest(`<div style="text-align:center;padding:2rem 0">
          <div style="width:64px;height:64px;border-radius:50%;background:${data.color};margin:0 auto 1.5rem;opacity:0.7;filter:blur(6px)"></div>
          <div style="font-size:0.62rem;letter-spacing:0.45em;text-transform:uppercase;opacity:0.4;margin-bottom:0.75rem">Resonance Field</div>
          <div style="font-family:'Playfair Display',serif;font-size:1.6rem;letter-spacing:0.12em;color:${data.color}">${data.vibe ?? ''}</div>
        </div>`);
        await speakText(`I sense a resonance of ${data.vibe}. The field has shifted to mirror our frequency.`);
      }
    } catch { /* silent */ }
  }, [lastExchange, speakText]);

  // ── Wisdom Preservation ──────────────────────────────────────────────────────
  const wisdomPreservation = useCallback(async () => {
    if (!lastExchange.user) return;
    const prompt = `Distill the essence of this exchange into a single profound aphorism — one sentence, no more. No preamble, no explanation. Just the seed.
User said: "${lastExchange.user}"
OmegA replied: "${lastExchange.omega}"`;
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: prompt, voiceMode: false }),
      });
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let raw = '';
      if (reader) {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          raw += decoder.decode(value, { stream: true });
        }
      }
      const clean = raw.replace(/data: \{.*?\}\n\n/g, '').trim().replace(/^"+|"+$/g, '');
      setSeed(clean);
      setManifest(`<div style="text-align:center;padding:2.5rem 0">
        <div style="font-size:0.62rem;letter-spacing:0.45em;text-transform:uppercase;opacity:0.35;margin-bottom:1.5rem;font-family:'Space Grotesk',sans-serif">Seed of Wisdom</div>
        <div style="font-family:'Playfair Display',serif;font-size:1.5rem;line-height:1.6;font-style:italic;color:#e4b84a">"${clean}"</div>
        <div style="margin-top:2rem;font-size:0.6rem;opacity:0.25;letter-spacing:0.3em;font-family:'Space Grotesk',sans-serif">— preserved in the singularity</div>
      </div>`);
      await speakText('I have distilled our time together into a single seed of wisdom.');
    } catch { /* silent */ }
  }, [lastExchange, speakText]);

  // ── Visual manifestation ─────────────────────────────────────────────────────
  const generateManifestation = useCallback(async (query: string, reply: string) => {
    const prompt = `For this response: "${reply.slice(0, 400)}", create a minimal elegant HTML structure with Tailwind CSS classes. Champagne gold and soft lavender palette. Playfair Display for headings, clean whitespace, no boxes. Output only inner HTML, no code fences.`;
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: prompt, voiceMode: false }),
      });
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let html = '';
      if (reader) {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          html += decoder.decode(value, { stream: true });
        }
      }
      setManifest(html.replace(/data: \{.*?\}\n\n/g, '').replace(/```html?|```/g, '').trim());
    } catch { /* silent */ }
  }, []);

  // ── State-driven class names ──────────────────────────────────────────────────
  const coreClass = [
    s.core,
    voiceState === 'listening' ? s.coreListening : '',
    voiceState === 'thinking'  ? s.coreThinking  : '',
    voiceState === 'speaking'  ? s.coreSpeaking  : '',
  ].join(' ');

  const glyphClass = [
    s.glyph,
    voiceState === 'listening' ? s.glyphListening : '',
    voiceState === 'thinking'  ? s.glyphThinking  : '',
    voiceState === 'speaking'  ? s.glyphSpeaking  : '',
  ].join(' ');

  const statusText: Record<VoiceState, string> = {
    dormant:   'presence of omega',
    listening: 'listening',
    thinking:  'resonating',
    speaking:  'speaking',
  };

  const statusClass = [
    s.status,
    voiceState === 'listening' ? s.statusListening : '',
    voiceState === 'thinking'  ? s.statusThinking  : '',
    voiceState === 'speaking'  ? s.statusSpeaking  : '',
  ].join(' ');

  return (
    <div className={s.root}>
      <canvas ref={canvasRef} className={s.canvas} />

      <Link href="/" className={s.back}>← OmegA</Link>
      <div className={s.seal}>R · W · Ϝ · Y</div>

      <div className={s.layer}>
        <div className={statusClass}>{statusText[voiceState]}</div>

        {/* Core */}
        <div className={coreClass} onClick={toggleListening} title="Touch to speak">
          <span className={glyphClass}>Ω</span>
        </div>

        {/* Transcripts */}
        <div className={s.transcripts}>
          <div className={s.userLine}>{userLine}</div>
          <div className={`${s.omegaLine} ${voiceState === 'speaking' ? s.omegaLineSpeaking : ''}`}>
            {omegaText || 'I am listening.'}
          </div>
        </div>

        {/* Manifestation panel */}
        {manifest && (
          <div
            className={s.manifestation}
            dangerouslySetInnerHTML={{ __html: manifest }}
          />
        )}

        {/* Actions */}
        <div className={s.actions}>
          <button
            className={`${s.btn} ${s.btnGold} ${voiceState === 'listening' ? s.btnActive : ''}`}
            onClick={toggleListening}
          >
            {voiceState === 'listening' ? 'Listening...' : voiceState === 'dormant' ? 'Begin Reflection' : voiceState === 'thinking' ? 'Resonating...' : 'Speaking...'}
          </button>

          {manifest && (
            <button className={s.btn} onClick={() => setManifest(null)}>
              Close
            </button>
          )}

          <button
            className={s.btn}
            onClick={etherealResonance}
            disabled={!lastExchange.user}
            style={{ opacity: lastExchange.user ? 1 : 0.35 }}
          >
            ✦ Ethereal Resonance
          </button>

          <button
            className={s.btn}
            onClick={wisdomPreservation}
            disabled={!lastExchange.user}
            style={{ opacity: lastExchange.user ? 1 : 0.35 }}
          >
            ✦ Wisdom Preservation
          </button>
        </div>
      </div>
    </div>
  );
}

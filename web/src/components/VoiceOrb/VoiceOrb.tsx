'use client';

import { useEffect, useRef } from 'react';
import type { VoiceState } from '@/hooks/useVoiceEngine';
import s from './VoiceOrb.module.css';

interface VoiceOrbProps {
  voiceState: VoiceState;
  micLevel?: number;   // 0-1
  ttsLevel?: number;   // 0-1
  thinking?: boolean;  // OmegA is processing
  size?: number;
}

export default function VoiceOrb({
  voiceState,
  micLevel = 0,
  ttsLevel = 0,
  thinking = false,
  size = 220,
}: VoiceOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<number>(0);
  const phaseRef = useRef(0);

  const activeLevel = voiceState === 'speaking' ? ttsLevel : micLevel;
  const isActive = voiceState !== 'dormant';

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = size * 2; // retina
    canvas.width = W;
    canvas.height = W;
    const C = W / 2;
    const R = C * 0.32; // core radius

    const draw = () => {
      phaseRef.current += 0.018;
      const ph = phaseRef.current;
      const lv = activeLevel;

      ctx.clearRect(0, 0, W, W);

      // ── Outer ambient glow ──────────────────────────────────────────────────
      const ambientR = C * 0.85 + lv * C * 0.12;
      const ambient = ctx.createRadialGradient(C, C, R * 0.5, C, C, ambientR);

      if (thinking) {
        ambient.addColorStop(0, 'rgba(228,184,74,0.12)');
        ambient.addColorStop(0.5, 'rgba(228,184,74,0.04)');
        ambient.addColorStop(1, 'rgba(0,0,0,0)');
      } else if (voiceState === 'listening' || voiceState === 'followup') {
        ambient.addColorStop(0, 'rgba(99,102,241,0.18)');
        ambient.addColorStop(0.5, 'rgba(139,92,246,0.06)');
        ambient.addColorStop(1, 'rgba(0,0,0,0)');
      } else if (voiceState === 'speaking') {
        ambient.addColorStop(0, 'rgba(196,181,253,0.20)');
        ambient.addColorStop(0.5, 'rgba(139,92,246,0.07)');
        ambient.addColorStop(1, 'rgba(0,0,0,0)');
      } else {
        ambient.addColorStop(0, 'rgba(99,102,241,0.06)');
        ambient.addColorStop(1, 'rgba(0,0,0,0)');
      }
      ctx.fillStyle = ambient;
      ctx.fillRect(0, 0, W, W);

      // ── Pulse rings (3 rings, offset phase) ────────────────────────────────
      const ringCount = 3;
      for (let i = 0; i < ringCount; i++) {
        const offset = (i / ringCount) * Math.PI * 2;
        const pulse = Math.sin(ph * 0.8 + offset) * 0.5 + 0.5;
        const ringR = R * (1.5 + i * 0.55) + lv * R * 0.6 * (1 - i * 0.2);
        const alpha = isActive
          ? (thinking ? 0.55 : 0.35 + pulse * 0.25) * (1 - i * 0.2)
          : 0.08 + pulse * 0.04;

        let color: string;
        if (thinking) color = `rgba(228,184,74,${alpha})`;
        else if (voiceState === 'speaking') color = `rgba(196,181,253,${alpha})`;
        else if (voiceState === 'followup') color = `rgba(99,210,190,${alpha})`;
        else color = `rgba(139,92,246,${alpha})`;

        ctx.beginPath();
        ctx.arc(C, C, ringR, 0, Math.PI * 2);
        ctx.strokeStyle = color;
        ctx.lineWidth = thinking ? 1.5 : 1.0 + lv * 1.5;
        ctx.stroke();
      }

      // ── Waveform ring (when active) ─────────────────────────────────────────
      if (isActive && lv > 0.02) {
        const waveR = R * 1.35 + lv * R * 0.4;
        const points = 128;
        ctx.beginPath();
        for (let p = 0; p <= points; p++) {
          const angle = (p / points) * Math.PI * 2 - Math.PI / 2;
          const wave = Math.sin(angle * 8 + ph * 3) * lv * R * 0.18
                     + Math.sin(angle * 5 - ph * 2) * lv * R * 0.10;
          const r = waveR + wave;
          const x = C + Math.cos(angle) * r;
          const y = C + Math.sin(angle) * r;
          p === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.closePath();
        const waveAlpha = 0.4 + lv * 0.4;
        ctx.strokeStyle = thinking
          ? `rgba(228,184,74,${waveAlpha})`
          : voiceState === 'speaking'
          ? `rgba(196,181,253,${waveAlpha})`
          : `rgba(99,102,241,${waveAlpha})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // ── Rotating arc (thinking) ─────────────────────────────────────────────
      if (thinking) {
        ctx.save();
        ctx.translate(C, C);
        ctx.rotate(ph * 2.5);
        ctx.beginPath();
        ctx.arc(0, 0, R * 2.0, 0, Math.PI * 1.2);
        ctx.strokeStyle = 'rgba(228,184,74,0.7)';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.stroke();
        ctx.rotate(Math.PI);
        ctx.beginPath();
        ctx.arc(0, 0, R * 2.0, 0, Math.PI * 0.5);
        ctx.strokeStyle = 'rgba(228,184,74,0.35)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.restore();
      }

      // ── Core glow ───────────────────────────────────────────────────────────
      const coreGlow = ctx.createRadialGradient(C, C, 0, C, C, R * 1.3);
      const breathe = Math.sin(ph * 0.7) * 0.5 + 0.5;

      if (thinking) {
        coreGlow.addColorStop(0, `rgba(255,230,130,${0.25 + breathe * 0.15})`);
        coreGlow.addColorStop(0.4, `rgba(228,184,74,${0.15 + breathe * 0.10})`);
        coreGlow.addColorStop(1, 'rgba(0,0,0,0)');
      } else if (voiceState === 'speaking') {
        coreGlow.addColorStop(0, `rgba(220,200,255,${0.22 + lv * 0.2})`);
        coreGlow.addColorStop(0.4, `rgba(139,92,246,${0.14 + lv * 0.1})`);
        coreGlow.addColorStop(1, 'rgba(0,0,0,0)');
      } else if (voiceState === 'listening') {
        coreGlow.addColorStop(0, `rgba(140,120,255,${0.20 + lv * 0.25})`);
        coreGlow.addColorStop(0.4, `rgba(99,102,241,${0.10 + lv * 0.15})`);
        coreGlow.addColorStop(1, 'rgba(0,0,0,0)');
      } else if (voiceState === 'followup') {
        coreGlow.addColorStop(0, `rgba(99,210,190,${0.18 + breathe * 0.08})`);
        coreGlow.addColorStop(0.4, `rgba(16,185,129,${0.10})`);
        coreGlow.addColorStop(1, 'rgba(0,0,0,0)');
      } else {
        coreGlow.addColorStop(0, `rgba(99,102,241,${0.10 + breathe * 0.05})`);
        coreGlow.addColorStop(1, 'rgba(0,0,0,0)');
      }
      ctx.fillStyle = coreGlow;
      ctx.beginPath();
      ctx.arc(C, C, R * 1.3, 0, Math.PI * 2);
      ctx.fill();

      frameRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(frameRef.current);
  }, [voiceState, thinking, activeLevel, isActive, size]);

  const stateClass = thinking ? s.thinking
    : voiceState === 'listening' ? s.listening
    : voiceState === 'speaking' ? s.speaking
    : voiceState === 'followup' ? s.followup
    : s.dormant;

  return (
    <div className={`${s.orbWrap} ${stateClass}`} style={{ width: size, height: size }}>
      <canvas ref={canvasRef} className={s.canvas} style={{ width: size, height: size }} />
      <div className={s.symbol}>Ω</div>
    </div>
  );
}

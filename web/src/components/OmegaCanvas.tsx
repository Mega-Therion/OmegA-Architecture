"use client";

import { useEffect, useRef } from "react";

export type CanvasState = "idle" | "thinking" | "responding";

interface Particle {
  x: number; y: number;
  vx: number; vy: number;
  size: number;
  opacity: number;
  rgb: string;
  phase: number;
  phaseSpeed: number;
}

interface FieldLine {
  pts: number[];   // x0,y0, cx1,cy1, cx2,cy2, x1,y1
  vel: number[];   // dx for each control point
  opacity: number;
}

function hex(h: string): string {
  const r = parseInt(h.slice(1, 3), 16);
  const g = parseInt(h.slice(3, 5), 16);
  const b = parseInt(h.slice(5, 7), 16);
  return `${r},${g},${b}`;
}

const COLORS = ["#3b4fd8", "#6d4ff5", "#9b7cfa", "#c4b5fd", "#818cf8"].map(hex);

export default function OmegaCanvas({ state }: { state: CanvasState }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  useEffect(() => { stateRef.current = state; }, [state]);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf: number;
    let W = 0, H = 0;
    let frame = 0;

    const resize = () => {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", resize);
    resize();

    // Particles
    const COUNT = 140;
    const particles: Particle[] = Array.from({ length: COUNT }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      size: Math.random() * 1.8 + 0.4,
      opacity: Math.random() * 0.55 + 0.1,
      rgb: COLORS[Math.floor(Math.random() * COLORS.length)],
      phase: Math.random() * Math.PI * 2,
      phaseSpeed: 0.008 + Math.random() * 0.018,
    }));

    // Field lines
    const LINES = 10;
    const lines: FieldLine[] = Array.from({ length: LINES }, () => ({
      pts: [
        Math.random() * W, Math.random() * H,
        Math.random() * W, Math.random() * H,
        Math.random() * W, Math.random() * H,
        Math.random() * W, Math.random() * H,
      ],
      vel: Array.from({ length: 8 }, () => (Math.random() - 0.5) * 0.25),
      opacity: Math.random() * 0.07 + 0.02,
    }));

    const draw = () => {
      raf = requestAnimationFrame(draw);
      frame++;

      const s = stateRef.current;
      const speed = s === "thinking" ? 2.8 : s === "responding" ? 1.6 : 1;
      const glow = s === "thinking" ? 0.18 + 0.12 * Math.sin(frame * 0.08) : s === "responding" ? 0.08 : 0;

      // Trailing clear
      ctx.fillStyle = "rgba(2, 2, 12, 0.18)";
      ctx.fillRect(0, 0, W, H);

      // Central pulse glow when thinking
      if (glow > 0) {
        const g = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.min(W, H) * 0.55);
        g.addColorStop(0, `rgba(99,60,220,${glow})`);
        g.addColorStop(0.5, `rgba(60,40,180,${glow * 0.4})`);
        g.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, W, H);
      }

      // Field lines
      for (const fl of lines) {
        for (let i = 0; i < fl.pts.length; i++) {
          fl.pts[i] += fl.vel[i] * speed;
          if (fl.pts[i] < -200 || fl.pts[i] > (i % 2 === 0 ? W : H) + 200) fl.vel[i] *= -1;
        }
        const [x0, y0, cx1, cy1, cx2, cy2, x1, y1] = fl.pts;
        const grad = ctx.createLinearGradient(x0, y0, x1, y1);
        const op = fl.opacity * (s === "thinking" ? 2.2 : s === "responding" ? 1.4 : 1);
        grad.addColorStop(0, `rgba(80,50,220,0)`);
        grad.addColorStop(0.5, `rgba(110,70,240,${op})`);
        grad.addColorStop(1, `rgba(80,50,220,0)`);
        ctx.beginPath();
        ctx.moveTo(x0, y0);
        ctx.bezierCurveTo(cx1, cy1, cx2, cy2, x1, y1);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Connections
      const maxDist = s === "thinking" ? 110 : 85;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < maxDist) {
            const a = (1 - d / maxDist) * 0.12 * (s === "thinking" ? 2.5 : 1);
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(120,80,255,${a})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      // Particles
      for (const p of particles) {
        p.x += p.vx * speed;
        p.y += p.vy * speed;
        p.phase += p.phaseSpeed * speed;
        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;

        const pulse = 0.5 + 0.5 * Math.sin(p.phase);
        const op = p.opacity * pulse * (s === "thinking" ? 1.5 : 1);
        const sz = p.size * (0.7 + 0.3 * pulse);

        // Soft glow
        const grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, sz * 5);
        grd.addColorStop(0, `rgba(${p.rgb},${op})`);
        grd.addColorStop(1, `rgba(${p.rgb},0)`);
        ctx.beginPath();
        ctx.arc(p.x, p.y, sz * 5, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();

        // Core
        ctx.beginPath();
        ctx.arc(p.x, p.y, sz, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${p.rgb},${Math.min(op * 2, 1)})`;
        ctx.fill();
      }

      // Arc sparks when thinking
      if (s === "thinking" && frame % 8 === 0) {
        const cx = W / 2 + (Math.random() - 0.5) * 60;
        const cy = H / 2 + (Math.random() - 0.5) * 60;
        ctx.beginPath();
        ctx.arc(cx, cy, Math.random() * 80 + 20, 0, Math.PI * 2 * Math.random());
        ctx.strokeStyle = `rgba(180,140,255,${Math.random() * 0.15})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }
    };

    draw();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      style={{
        position: "fixed", inset: 0,
        width: "100%", height: "100%",
        zIndex: 0, pointerEvents: "none",
        background: "#02020c",
      }}
    />
  );
}

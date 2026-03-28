"use client";

import { useState, useRef, useCallback } from "react";
import s from "./Landing.module.css";

interface LandingProps {
  onFirstMessage: (text: string) => void;
  isThinking?: boolean;
}

const FEATURES = [
  {
    icon: "\u039C",
    title: "Persistent Memory",
    desc: "MYELIN graph memory hardens retrieval paths with use — nothing is forgotten.",
  },
  {
    icon: "\u03A6",
    title: "Identity Anchoring",
    desc: "AEON Phylactery chain ensures cryptographic continuity of self across sessions.",
  },
  {
    icon: "\u03A3",
    title: "Synthesis Engine",
    desc: "ADCCL cognitive control loop with claim budgets and anti-drift self-tagging.",
  },
  {
    icon: "\u0391",
    title: "Governed Reasoning",
    desc: "AEGIS policy shell enforces model-agnostic governance at the API boundary.",
  },
];

export default function Landing({ onFirstMessage, isThinking = false }: LandingProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoResize = () => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
  };

  const handleSubmit = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      const text = input.trim();
      if (!text || isThinking) return;
      setInput("");
      onFirstMessage(text);
    },
    [input, isThinking, onFirstMessage],
  );

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={s.landing}>
      <div className={s.vignette} />

      {/* Hero */}
      <div className={s.hero}>
        {isThinking && (
          <div className={s.ringWrap}>
            <div className={s.ring} />
            <div className={s.ring} />
            <div className={s.ring} />
          </div>
        )}

        <div
          className={`${s.omega} ${isThinking ? s.thinking : ""}`}
        >
          {"\u03A9"}
        </div>

        <div className={s.titleStack}>
          <div className={s.title}>OmegA</div>
          <div className={s.subtitle}>Sovereign. Persistent. Self-Knowing.</div>
          <div className={s.byline}>Engineered by R.W. Yett</div>
        </div>
      </div>

      {/* Feature Cards */}
      <div className={s.featureStrip}>
        {FEATURES.map((f) => (
          <div key={f.title} className={s.card}>
            <div className={s.cardIcon}>{f.icon}</div>
            <div className={s.cardTitle}>{f.title}</div>
            <div className={s.cardDesc}>{f.desc}</div>
          </div>
        ))}
      </div>

      {/* Thinking indicator */}
      {isThinking && (
        <div className={s.thinkingDots}>
          <span />
          <span />
          <span />
        </div>
      )}

      {/* Input */}
      <div className={s.inputSection}>
        <div className={s.inputLabel}>Begin a conversation</div>
        <div className={s.inputWrap}>
          <form onSubmit={handleSubmit}>
            <div className={s.inputBar}>
              <textarea
                ref={textareaRef}
                className={s.textarea}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  autoResize();
                }}
                onKeyDown={handleKey}
                placeholder="Begin a conversation..."
                rows={1}
                disabled={isThinking}
                autoFocus
              />
              <button
                className={s.sendBtn}
                type="submit"
                disabled={!input.trim() || isThinking}
                aria-label="Send message"
              >
                {"\u03A9"}
              </button>
            </div>
          </form>
          <div className={s.inputHint}>&crarr; to send</div>
        </div>
      </div>

      {/* Footer */}
      <footer className={s.footer}>
        <a href="/about" className={s.footerLink}>
          About OmegA
        </a>
      </footer>
    </div>
  );
}

"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chat } from "@/lib/api";
import type { CanvasState } from "@/components/OmegaCanvas";
import s from "./page.module.css";

const OmegaCanvas = dynamic(() => import("@/components/OmegaCanvas"), { ssr: false });

// ── Typewriter hook ───────────────────────────────────────────────
function useTypewriter(text: string, speed = 12) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed("");
    setDone(false);
    if (!text) return;
    let i = 0;
    const id = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) { clearInterval(id); setDone(true); }
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);

  return { displayed, done };
}

// ── Types ─────────────────────────────────────────────────────────
interface Msg { role: "user" | "omega"; text: string; }

// ── OmegA message with typewriter ────────────────────────────────
function OmegaMsg({ text, animate }: { text: string; animate: boolean }) {
  const { displayed, done } = useTypewriter(animate ? text : "", 11);
  const content = animate ? displayed : text;
  const streaming = animate && !done;
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className={s.msgOmega}>
      <span className={s.omegaGlyph}>Ω</span>
      <div className={s.omegaBody}>
        <div className={`${s.omegaText} ${streaming ? s.streaming : ""}`}>
          {streaming ? (
            <>{content}<span className={s.cursor} /></>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          )}
        </div>
        {!streaming && (
          <button className={s.copyBtn} onClick={copy} title="Copy">
            {copied ? "✓ Copied" : "Copy"}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────
export default function Home() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [canvasState, setCanvasState] = useState<CanvasState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [latestOmega, setLatestOmega] = useState("");
  const [animatingIdx, setAnimatingIdx] = useState(-1);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const inChatMode = messages.length > 0;

  const newChat = () => {
    setMessages([]);
    setInput("");
    setError(null);
    setCanvasState("idle");
    setLatestOmega("");
    setAnimatingIdx(-1);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, canvasState]);

  const send = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || canvasState === "thinking") return;

    setInput("");
    setError(null);
    setMessages(prev => [...prev, { role: "user", text }]);
    setCanvasState("thinking");
    setLatestOmega("");

    try {
      const res = await chat({ user: text });
      const reply = res.reply ?? res.response ?? "";
      setMessages(prev => {
        const next = [...prev, { role: "omega" as const, text: reply }];
        setAnimatingIdx(next.length - 1);
        return next;
      });
      setLatestOmega(reply);
      setCanvasState("responding");
      // Return to idle after animation
      setTimeout(() => setCanvasState("idle"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setCanvasState("idle");
    }
  }, [input, canvasState]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  // ── Render ───────────────────────────────────────────────────────
  return (
    <>
      <OmegaCanvas state={canvasState} />

      <div className={s.root}>
        {!inChatMode ? (
          /* ── LANDING ── */
          <>
            <div className={s.landing}>
              {canvasState === "thinking" && (
                <div className={s.ringWrap}>
                  <div className={s.ring} />
                  <div className={s.ring} />
                  <div className={s.ring} />
                </div>
              )}
              <div className={`${s.landingOmega} ${canvasState === "thinking" ? s.thinking : canvasState === "responding" ? s.responding : ""}`}>
                Ω
              </div>
              <div className={s.landingTitle}>OmegA</div>
              <div className={s.landingTagline}>Sovereign Intelligence</div>
            </div>

            {canvasState === "thinking" && (
              <div style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, 110px)", textAlign: "center" }}>
                <div className={s.thinkingDots}>
                  <span /><span /><span />
                </div>
              </div>
            )}

            <div className={s.landingInput}>
              <div style={{ maxWidth: 640, margin: "0 auto" }}>
                <form onSubmit={send}>
                  <div className={s.inputBar}>
                    <textarea
                      ref={textareaRef}
                      className={s.textarea}
                      value={input}
                      onChange={e => { setInput(e.target.value); autoResize(); }}
                      onKeyDown={handleKey}
                      placeholder="Ask OmegA anything…"
                      rows={1}
                      disabled={canvasState === "thinking"}
                    />
                    <button className={s.sendBtn} type="submit" disabled={!input.trim() || canvasState === "thinking"}>
                      Ω
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </>
        ) : (
          /* ── CHAT ── */
          <>
            <header className={s.header}>
              <span className={`${s.headerOmega} ${canvasState === "thinking" ? s.thinking : ""}`}>Ω</span>
              <span className={s.headerName}>OmegA</span>
              <div className={s.headerStatus}>
                <div className={s.statusDot} />
                Sovereign
              </div>
              <button className={s.newChatBtn} onClick={newChat} title="New chat">
                + New
              </button>
            </header>

            <div className={s.feed}>
              {messages.map((msg, i) =>
                msg.role === "user" ? (
                  <div key={i} className={s.msgUser}>{msg.text}</div>
                ) : (
                  <OmegaMsg key={i} text={msg.text} animate={i === animatingIdx} />
                )
              )}

              {canvasState === "thinking" && (
                <div className={s.thinking}>
                  <span className={s.omegaGlyph}>Ω</span>
                  <div className={s.thinkingDots}>
                    <span /><span /><span />
                  </div>
                  <span className={s.thinkingLabel}>processing</span>
                </div>
              )}

              {error && <div className={s.error}>⚠ {error}</div>}
              <div ref={bottomRef} style={{ height: 1 }} />
            </div>

            <div className={s.inputWrap}>
              <form onSubmit={send}>
                <div className={s.inputBar}>
                  <textarea
                    ref={textareaRef}
                    className={s.textarea}
                    value={input}
                    onChange={e => { setInput(e.target.value); autoResize(); }}
                    onKeyDown={handleKey}
                    placeholder="Ask OmegA anything…"
                    rows={1}
                    disabled={canvasState === "thinking"}
                  />
                  <button className={s.sendBtn} type="submit" disabled={!input.trim() || canvasState === "thinking"}>
                    Ω
                  </button>
                </div>
              </form>
            </div>
          </>
        )}
      </div>
    </>
  );
}

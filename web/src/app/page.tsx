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

// ── CodeBlock ─────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CodeBlock({ inline, className, children, ...props }: any) {
  const match = /language-(\w+)/.exec(className || "");
  const [copied, setCopied] = useState(false);
  
  const hCopy = () => {
    navigator.clipboard.writeText(String(children).replace(/\n$/, ""));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!inline && match) {
    return (
      <div className={`${s.codeBlockWrap} ${s.staggerBlock}`}>
        <div className={s.codeHeader}>
          <span className={s.codeLang}>{match[1]}</span>
          <button className={s.codeCopyBtn} onClick={hCopy} aria-label="Copy code">
            {copied ? "✓ Copied" : "Copy"}
          </button>
        </div>
        <pre className={s.codePre}><code className={className} {...props}>{children}</code></pre>
      </div>
    );
  }
  return <code className={className} {...props}>{children}</code>;
}

// ── Markdown Components ───────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mdComponents: any = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  p: ({ children }: any) => <p className={s.staggerBlock}>{children}</p>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  h1: ({ children }: any) => <h1 className={s.staggerBlock}>{children}</h1>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  h2: ({ children }: any) => <h2 className={s.staggerBlock}>{children}</h2>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  h3: ({ children }: any) => <h3 className={s.staggerBlock}>{children}</h3>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ul: ({ children }: any) => <ul className={s.staggerBlock}>{children}</ul>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ol: ({ children }: any) => <ol className={s.staggerBlock}>{children}</ol>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  blockquote: ({ children }: any) => <blockquote className={s.staggerBlock}>{children}</blockquote>,
  code: CodeBlock,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  table: ({ children }: any) => (
    <div className={`${s.tableWrap} ${s.staggerBlock}`}>
      <table>{children}</table>
    </div>
  )
};

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
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{content}</ReactMarkdown>
          )}
        </div>
        {!streaming && (
          <button
            className={s.copyBtn}
            onClick={copy}
            title="Copy"
            aria-label={copied ? "Copied to clipboard" : "Copy response"}
          >
            {copied ? "✓ Copied" : "Copy"}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Thinking Indicator ───────────────────────────────────────────
const THINKING_STATES = ["reading memory...", "synthesizing...", "forming response..."];

function ThinkingIndicator() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setIdx(i => (i + 1) % THINKING_STATES.length), 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className={s.thinkingIndicator}>
      <span className={s.omegaGlyph}>Ω</span>
      <div className={s.thinkingContent}>
        <div className={s.thinkingDots}>
          <span /><span /><span />
        </div>
        <div className={s.thinkingLabelWrap}>
          {THINKING_STATES.map((txt, i) => (
            <span key={txt} className={`${s.thinkingLabelItem} ${i === idx ? s.active : ""}`}>
              {txt}
            </span>
          ))}
        </div>
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
  const [showPill, setShowPill] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const inChatMode = messages.length > 0;

  // Suppress unused-var lint — latestOmega is retained for future streaming use
  void latestOmega;

  const newChat = () => {
    setMessages([]);
    setInput("");
    setError(null);
    setCanvasState("idle");
    setLatestOmega("");
    setAnimatingIdx(-1);
    setShowPill(false);
  };

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    setShowPill(false);
  };

  const handleScroll = () => {
    const el = feedRef.current;
    if (!el) return;
    const isBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
    setShowPill(!isBottom);
  };

  useEffect(() => {
    if (!showPill) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, canvasState, showPill]);

  const send = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || canvasState === "thinking") return;

    setInput("");
    setError(null);
    setMessages(prev => [...prev, { role: "user", text }]);
    setCanvasState("thinking");
    setLatestOmega("");
    setShowPill(false);

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
              <div className={s.vignettePulse} />
              
              <div className={s.heroSection}>
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
                <div className={s.taglineStack}>
                  <div className={s.tagline1}>Ω OmegA</div>
                  <div className={s.tagline2}>Sovereign Intelligence</div>
                  <div className={s.tagline3}>Engineered by Ryan Wayne Yett</div>
                </div>
              </div>

              <div className={s.featureStrip}>
                <div className={s.featureCard}>
                  <div className={s.featureIcon}>M</div>
                  <div className={s.featureTitle}>Persistent Memory</div>
                  <div className={s.featureDesc}>MYELIN layer</div>
                </div>
                <div className={s.featureCard}>
                  <div className={s.featureIcon}>A</div>
                  <div className={s.featureTitle}>Identity-Anchored</div>
                  <div className={s.featureDesc}>AEON / CAR principle</div>
                </div>
                <div className={s.featureCard}>
                  <div className={s.featureIcon}>G</div>
                  <div className={s.featureTitle}>Governed Reasoning</div>
                  <div className={s.featureDesc}>AEGIS layer</div>
                </div>
              </div>

              {canvasState === "thinking" && (
                <div className={s.landingThinkingContainer}>
                  <div className={s.thinkingDots}>
                    <span /><span /><span />
                  </div>
                </div>
              )}

              <div className={s.landingInputWrap}>
                <div className={s.inputEyebrow}>Ask OmegA anything</div>
                <div className={s.inputContainerMaxWidth}>
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
                      <button
                        className={s.sendBtn}
                        type="submit"
                        disabled={!input.trim() || canvasState === "thinking"}
                        aria-label="Send message"
                      >
                        Ω
                      </button>
                    </div>
                  </form>
                </div>
                <div className={s.inputHint}>&crarr; to send</div>
              </div>

              <div className={s.scrollHint}>
                <span className={s.chevron}></span>
                <span className={s.chevron}></span>
                <span className={s.chevron}></span>
              </div>
              
              <footer className={s.landingFooter}>
                <a href="/about" className={s.footerLink}>ABOUT OMEGA</a>
              </footer>
            </div>
          </>
        ) : (
          /* ── CHAT ── */
          <>
            <header className={`${s.header} ${canvasState === "thinking" ? s.headerThinking : ""}`}>
              <div className={s.headerInner}>
                <span className={`${s.headerOmega} ${canvasState === "thinking" ? s.thinking : ""}`}>Ω</span>
                <span className={s.headerName}>OmegA</span>
                <div className={s.headerStatus}>
                  <div className={s.statusDot} />
                  Sovereign
                </div>
                <div className={s.headerSession}>Session active</div>
                <button
                  className={s.newChatBtn}
                  onClick={newChat}
                  title="New chat"
                  aria-label="Start new chat"
                >
                  + New
                </button>
              </div>
              <div className={s.headerGradientLine} />
            </header>

            <div
              className={s.feed}
              role="log"
              aria-live="polite"
              aria-label="Chat messages"
              ref={feedRef}
              onScroll={handleScroll}
            >
              {messages.map((msg, i) =>
                msg.role === "user" ? (
                  <div key={i} className={s.msgUser}>{msg.text}</div>
                ) : (
                  <OmegaMsg key={i} text={msg.text} animate={i === animatingIdx} />
                )
              )}

              {canvasState === "thinking" && <ThinkingIndicator />}

              {error && <div className={s.error} role="alert">⚠ {error}</div>}
              <div ref={bottomRef} style={{ height: 1 }} />
            </div>

            {showPill && (
              <div className={s.scrollPillWrap}>
                <button className={s.scrollPill} onClick={scrollToBottom} aria-label="Scroll to bottom">
                  ↓ New response
                </button>
              </div>
            )}

            <div className={s.inputWrap}>
              <form onSubmit={send}>
                <div className={`${s.inputBar} ${input.trim() ? s.hasInput : ''}`}>
                  <button type="button" className={s.attachBtn} aria-label="Attach file" disabled={canvasState === "thinking"}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{opacity: 0.6}}><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
                  </button>
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
                  {input.length > 200 && (
                    <div className={s.charCount}>{input.length}</div>
                  )}
                  <button
                    className={`${s.sendBtn} ${input.trim() ? s.pulse : ''}`}
                    type="submit"
                    disabled={!input.trim() || canvasState === "thinking"}
                    aria-label="Send message"
                  >
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

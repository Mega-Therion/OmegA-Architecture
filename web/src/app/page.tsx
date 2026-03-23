"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chatStream } from "@/lib/api";
import type { CanvasState } from "@/components/OmegaCanvas";
import s from "./page.module.css";

const OmegaCanvas = dynamic(() => import("@/components/OmegaCanvas"), { ssr: false });

// Removed useTypewriter Hook — upgraded to real streaming

// ── Types ─────────────────────────────────────────────────────────
interface Msg { role: "user" | "omega"; text: string; timestamp?: string; }

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

// ── OmegA message with streaming ─────────────────────────────────
function OmegaMsg({ text, animate, timestamp }: { text: string; animate: boolean; timestamp?: string }) {
  const streaming = animate;
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
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{text}</ReactMarkdown>
          {streaming && <span className={s.cursor} />}
        </div>
        {!streaming && (
          <div className={s.omegaFooter}>
            {timestamp && <span className={s.msgTimestamp}>{new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>}
            <button
              className={s.copyBtn}
              onClick={copy}
              title="Copy"
              aria-label={copied ? "Copied to clipboard" : "Copy response"}
            >
              {copied ? "✓ Copied" : "Copy"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Thinking Indicator ───────────────────────────────────────────
const THINKING_STATES = ["reading memory...", "synthesizing...", "forming response..."];

function ThinkingIndicator({ status }: { status?: string | null }) {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setIdx(i => (i + 1) % THINKING_STATES.length), 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className={s.thinkingIndicator}>
      <span className={s.omegaGlyph}>Ω</span>
      <div className={s.thinkingContent}>
        {status ? (
          <div className={s.thinkingStatusText}>{status}</div>
        ) : (
          <>
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
          </>
        )}
      </div>
    </div>
  );
}

function formatRelativeTime(dateStr: string) {
  if (!dateStr) return "";
  const diff = Math.max(0, Date.now() - new Date(dateStr).getTime());
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return `just now`;
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return `yesterday`;
  return `${days}d ago`;
}

// ── Main ──────────────────────────────────────────────────────────
export default function Home() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [animatingIdx, setAnimatingIdx] = useState<number>(-1);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [canvasState, setCanvasState] = useState<CanvasState>("idle");
  const [latestOmega, setLatestOmega] = useState("");
  const [showPill, setShowPill] = useState(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sessionList, setSessionList] = useState<{id: string; created_at: string; preview: string}[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inChatMode = messages.length > 0;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setHistoryOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (historyOpen) {
      fetch('/api/sessions').then(res => res.json()).then(data => {
        if (Array.isArray(data)) setSessionList(data);
      }).catch(console.error);
    }
  }, [historyOpen]);

  const loadSession = async (id: string) => {
    try {
      const res = await fetch(`/api/sessions/${id}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setMessages(data.map((m: any) => ({ role: m.role, text: m.content, timestamp: m.created_at })));
        setSessionId(id);
        localStorage.setItem("omega_session", id);
        setHistoryOpen(false);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const startNewSession = () => {
    setMessages([]);
    setAnimatingIdx(-1);
    setLatestOmega("");
    setSessionId(null);
    localStorage.removeItem("omega_session");
    setHistoryOpen(false);
  };
  
  const newChat = startNewSession;


  // Auto-resize
  const autoResize = () => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
  };

  useEffect(() => {
    const saved = localStorage.getItem("omega_session");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (saved) setSessionId(saved);
  }, []);
  // Suppress unused-var lint — latestOmega is retained for future streaming use
  void latestOmega;

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
    const newMessage: Msg = { role: "user", text, timestamp: new Date().toISOString() };
    const currentMessages = [...messages];
    setMessages(prev => [...prev, newMessage]);
    setCanvasState("thinking");
    setLatestOmega("");
    setShowPill(false);

    try {
      const res = await chatStream(
        { user: text, history: currentMessages, sessionId: sessionId ?? undefined }, 
        (chunk) => {
          setStatusText(null); // First token arrives, clear status
          setMessages(prev => {
            const newMsgs = [...prev];
            const last = newMsgs[newMsgs.length - 1];
            if (last.role === "user") {
              newMsgs.push({ role: "omega", text: chunk, timestamp: new Date().toISOString() });
              setAnimatingIdx(newMsgs.length - 1);
              setCanvasState("idle");
            } else {
              newMsgs[newMsgs.length - 1] = { ...last, text: last.text + chunk };
            }
            return newMsgs;
          });
        },
        (status) => {
          setStatusText(status);
        }
      );
      
      if (res.sessionId && !sessionId) {
        setSessionId(res.sessionId);
        localStorage.setItem("omega_session", res.sessionId);
      }

      setAnimatingIdx(-1);
      setStatusText(null); // End of stream
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setCanvasState("idle");
      setStatusText(null);
    }
  }, [input, canvasState, messages, sessionId]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
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
                        autoFocus
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
                <div className={s.headerGroup}>
                  <button className={s.historyBtn} title="View Session History" onClick={() => setHistoryOpen(true)}>
                    ⌘ History
                  </button>
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
                  <div key={i} className={s.msgUserWrap}>
                    <div className={s.msgUser}>{msg.text}</div>
                    {msg.timestamp && <div className={s.msgTimestampUser}>{new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>}
                  </div>
                ) : (
                  <OmegaMsg key={i} text={msg.text} animate={i === animatingIdx} timestamp={msg.timestamp} />
                )
              )}

              {canvasState === "thinking" && <ThinkingIndicator status={statusText} />}

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
                    autoFocus
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

      {/* History Panel */}
      {historyOpen && <div className={s.historyOverlay} onClick={() => setHistoryOpen(false)} />}
      <div className={`${s.historyPanel} ${historyOpen ? s.open : ""}`}>
        <div className={s.historyPanelHeader}>
          <span>Session History</span>
          <button onClick={startNewSession}>+ New</button>
        </div>
        <div className={s.historyList}>
          {sessionList.map(session => (
            <div key={session.id} className={s.historyItem} onClick={() => loadSession(session.id)}>
              <span className={s.historyPreview}>
                {session.preview ? (session.preview.length > 60 ? session.preview.slice(0, 60) + "..." : session.preview) : "Empty Session"}
              </span>
              <span className={s.historyTime}>{formatRelativeTime(session.created_at)}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

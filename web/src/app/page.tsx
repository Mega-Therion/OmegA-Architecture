"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { chatStream } from "@/lib/api";
import type { CanvasState } from "@/components/OmegaCanvas";
import Landing from "@/components/Landing";
import Sidebar from "@/components/Sidebar/Sidebar";
import ChatHeader from "@/components/ChatHeader/ChatHeader";
import UserMessage from "@/components/MessageBubble/UserMessage";
import OmegaMessage from "@/components/MessageBubble/OmegaMessage";
import ThinkingIndicator from "@/components/MessageBubble/ThinkingIndicator";
import InputArea from "@/components/InputArea/InputArea";
import s from "./page.module.css";

const OmegaCanvas = dynamic(() => import("@/components/OmegaCanvas"), { ssr: false });

interface Msg {
  role: "user" | "omega";
  text: string;
  timestamp?: string;
  provider?: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [animatingIdx, setAnimatingIdx] = useState(-1);
  const [error, setError] = useState<string | null>(null);
  const [canvasState, setCanvasState] = useState<CanvasState>("idle");
  const [statusText, setStatusText] = useState<string | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessionList, setSessionList] = useState<{ id: string; created_at: string; preview: string }[]>([]);
  const [showPill, setShowPill] = useState(false);

  const feedRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inChatMode = messages.length > 0;

  // Load saved session on mount
  useEffect(() => {
    const saved = localStorage.getItem("omega_session");
    if (saved) setSessionId(saved);
  }, []);

  // Fetch session list for sidebar
  const refreshSessions = useCallback(() => {
    fetch("/api/sessions")
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setSessionList(data); })
      .catch(console.error);
  }, []);

  useEffect(() => { refreshSessions(); }, [refreshSessions]);

  // Scroll management
  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    setShowPill(false);
  };
  const handleScroll = () => {
    const el = feedRef.current;
    if (!el) return;
    setShowPill(el.scrollHeight - el.scrollTop - el.clientHeight > 50);
  };
  useEffect(() => {
    if (!showPill) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, canvasState, showPill]);

  // Core send logic (reusable for both landing and chat input)
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || canvasState === "thinking") return;
      setError(null);
      const newMsg: Msg = { role: "user", text, timestamp: new Date().toISOString() };
      const currentHistory = [...messages];
      setMessages((prev) => [...prev, newMsg]);
      setCanvasState("thinking");
      setShowPill(false);

      try {
        const res = await chatStream(
          { user: text, history: currentHistory, sessionId: sessionId ?? undefined },
          (chunk) => {
            setStatusText(null);
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "user") {
                updated.push({ role: "omega", text: chunk, timestamp: new Date().toISOString() });
                setAnimatingIdx(updated.length - 1);
                setCanvasState("idle");
              } else {
                updated[updated.length - 1] = { ...last, text: last.text + chunk };
              }
              return updated;
            });
          },
          (status) => setStatusText(status)
        );

        if (res.sessionId && !sessionId) {
          setSessionId(res.sessionId);
          localStorage.setItem("omega_session", res.sessionId);
        }
        if (res.provider) setProvider(res.provider);

        // Tag the last omega message with provider
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "omega") updated[updated.length - 1] = { ...last, provider: res.provider };
          return updated;
        });

        setAnimatingIdx(-1);
        setStatusText(null);
        refreshSessions();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setCanvasState("idle");
        setStatusText(null);
      }
    },
    [canvasState, messages, sessionId, refreshSessions]
  );

  const loadSession = async (id: string) => {
    try {
      const res = await fetch(`/api/sessions/${id}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setMessages(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          data.map((m: any) => ({ role: m.role, text: m.content, timestamp: m.created_at }))
        );
        setSessionId(id);
        localStorage.setItem("omega_session", id);
        setSidebarOpen(false);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setAnimatingIdx(-1);
    setSessionId(null);
    setProvider(null);
    localStorage.removeItem("omega_session");
    setSidebarOpen(false);
  };

  // ── Render ──────────────────────────────────────────────────────
  return (
    <>
      <OmegaCanvas state={canvasState} />

      <div className={s.appLayout}>
        <Sidebar
          sessions={sessionList}
          activeSessionId={sessionId}
          onNewChat={startNewChat}
          onSelectSession={loadSession}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen((o) => !o)}
        />

        <div className={s.mainArea}>
          {!inChatMode ? (
            <Landing
              onFirstMessage={sendMessage}
              isThinking={canvasState === "thinking"}
            />
          ) : (
            <>
              <ChatHeader
                provider={provider ?? undefined}
                thinking={canvasState === "thinking"}
                onToggleSidebar={() => setSidebarOpen((o) => !o)}
                onNewChat={startNewChat}
              />

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
                    <UserMessage key={i} text={msg.text} timestamp={msg.timestamp} />
                  ) : (
                    <OmegaMessage
                      key={i}
                      text={msg.text}
                      streaming={i === animatingIdx}
                      timestamp={msg.timestamp}
                      provider={msg.provider}
                    />
                  )
                )}

                {canvasState === "thinking" && <ThinkingIndicator status={statusText} />}

                {error && (
                  <div className={s.error} role="alert">
                    ⚠ {error}
                  </div>
                )}
                <div ref={bottomRef} style={{ height: 1 }} />
              </div>

              {showPill && (
                <div className={s.scrollPillWrap}>
                  <button className={s.scrollPill} onClick={scrollToBottom} aria-label="Scroll to bottom">
                    ↓ New response
                  </button>
                </div>
              )}

              <InputArea
                onSend={sendMessage}
                disabled={canvasState === "thinking"}
                autoFocus
              />
            </>
          )}
        </div>
      </div>
    </>
  );
}

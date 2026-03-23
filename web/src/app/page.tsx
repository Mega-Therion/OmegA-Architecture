"use client";

import { useState, useRef, useEffect } from "react";
import { chat } from "@/lib/api";
import styles from "./page.module.css";

interface Message {
  role: "user" | "omega";
  text: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setError(null);
    setMessages(prev => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const resp = await chat({ user: text, mode: "omega" });
      setMessages(prev => [...prev, { role: "omega", text: resp.reply ?? resp.response ?? "" }]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.shell}>
      {/* Header */}
      <header className={styles.header}>
        <span className={styles.omega}>Ω</span>
        <span className={styles.name}>OmegA</span>
      </header>

      {/* Message list */}
      <div className={styles.feed}>
        {messages.length === 0 && (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>Ask me anything.</p>
            <p className={styles.emptySubtitle}>
              I&apos;m OmegA — a sovereign AI built by Ryan Wayne Yett from Story, Arkansas.
              Ask about me, ask about him, or ask about anything else in the world.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={msg.role === "user" ? styles.bubbleUser : styles.bubbleOmega}
          >
            {msg.role === "omega" && <span className={styles.bubbleLabel}>Ω</span>}
            <p className={styles.bubbleText}>{msg.text}</p>
          </div>
        ))}

        {loading && (
          <div className={styles.bubbleOmega}>
            <span className={styles.bubbleLabel}>Ω</span>
            <p className={styles.thinking}>thinking…</p>
          </div>
        )}

        {error && (
          <p className={styles.error}>⚠ {error}</p>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className={styles.inputRow}>
        <textarea
          className={styles.input}
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask OmegA anything…"
          rows={1}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend(e);
            }
          }}
        />
        <button type="submit" className={styles.sendBtn} disabled={loading}>
          ↑
        </button>
      </form>
    </div>
  );
}

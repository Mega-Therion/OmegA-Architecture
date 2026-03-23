"use client";

import { useState, useEffect, useRef } from "react";
import IdentityShell from "@/components/IdentityShell";
import ConcentricCore from "@/components/ConcentricCore";
import SystemState from "@/components/SystemState";
import styles from "./page.module.css";
import {
  getSystemStatus,
  chat,
  queryMemory,
  type SystemStatus,
  type ChatResponse,
  type MemoryHit,
} from "@/lib/api";

export default function Home() {
  const [status, setStatus]           = useState<SystemStatus | null>(null);
  const [statusErr, setStatusErr]     = useState<string | null>(null);

  // Chat panel
  const [prompt, setPrompt]           = useState("");
  const [chatResp, setChatResp]       = useState<ChatResponse | null>(null);
  const [chatErr, setChatErr]         = useState<string | null>(null);
  const [chatLoading, setChatLoading] = useState(false);

  // Memory query panel
  const [memQuery, setMemQuery]       = useState("");
  const [memHits, setMemHits]         = useState<MemoryHit[]>([]);
  const [memErr, setMemErr]           = useState<string | null>(null);
  const [memLoading, setMemLoading]   = useState(false);

  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getSystemStatus()
      .then(setStatus)
      .catch((e: Error) => setStatusErr(e.message));
  }, []);

  async function handleChat(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setChatLoading(true);
    setChatErr(null);
    setChatResp(null);
    try {
      const resp = await chat({ user: prompt, namespace: "biography.ry", use_memory: true });
      setChatResp(resp);
      setPrompt("");
      setTimeout(() => chatRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (err: unknown) {
      setChatErr(err instanceof Error ? err.message : String(err));
    } finally {
      setChatLoading(false);
    }
  }

  async function handleMemoryQuery(e: React.FormEvent) {
    e.preventDefault();
    if (!memQuery.trim()) return;
    setMemLoading(true);
    setMemErr(null);
    setMemHits([]);
    try {
      const result = await queryMemory(memQuery, "default", 6);
      setMemHits(result.hits);
    } catch (err: unknown) {
      setMemErr(err instanceof Error ? err.message : String(err));
    } finally {
      setMemLoading(false);
    }
  }

  const enabledProviders = status?.providers.filter(p => p.enabled) ?? [];

  return (
    <main className={styles.main}>
      <IdentityShell />

      {/* ── Architecture overview ─────────────────────────────────────────── */}
      <section className={styles.hero}>
        <ConcentricCore />
        <SystemState />
      </section>

      {/* ── Architecture cards ────────────────────────────────────────────── */}
      <section className={styles.intro}>
        <div className={styles.introGrid}>
          <div className={`${styles.card} glass`}>
            <h3>Sovereign Identity</h3>
            <p>
              Moving identity, task state, and tool routing out of the prompt and into OS-level constructs.
              The Phylactery is a cryptographically chained identity log.
            </p>
          </div>
          <div className={`${styles.card} glass`}>
            <h3>Path-Dependent Memory</h3>
            <p>
              MYELIN replaces flat vector stores with a sparse graph whose edges carry semantic similarity,
              co-activation, and reward signals.
            </p>
          </div>
          <div className={`${styles.card} glass`}>
            <h3>Cognitive Control</h3>
            <p>
              ADCCL forces the system to externalize its intent into a Goal Contract and Claim Budget
              before any generation occurs.
            </p>
          </div>
        </div>
      </section>

      {/* ── Gateway status ────────────────────────────────────────────────── */}
      <section className={styles.backendStatus}>
        <h2 className={styles.sectionTitle}>Gateway Status</h2>

        {statusErr && <p className={styles.error}>⚠ {statusErr}</p>}
        {!status && !statusErr && <p className={styles.dimText}>Connecting to gateway…</p>}

        {status && (
          <div className={styles.statusGrid}>
            <div className={`${styles.statusCard} glass`}>
              <h3>Gateway</h3>
              <p><strong>Status:</strong> {status.gateway.status}</p>
              <p><strong>Version:</strong> {status.gateway.version}</p>
            </div>
            <div className={`${styles.statusCard} glass`}>
              <h3>Providers ({enabledProviders.length} active)</h3>
              <div className={styles.providerList}>
                {status.providers.map(p => (
                  <span
                    key={p.name}
                    className={`${styles.providerBadge} ${p.enabled ? styles.providerOn : styles.providerOff}`}
                  >
                    {p.name}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ── Chat panel ────────────────────────────────────────────────────── */}
      <section className={styles.chatSection}>
        <h2 className={styles.sectionTitle}>Ask OmegA</h2>
        <form onSubmit={handleChat} className={styles.chatForm}>
          <textarea
            className={styles.chatInput}
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="Send a message to OmegA… (Enter to send, Shift+Enter for newline)"
            rows={3}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleChat(e);
              }
            }}
          />
          <button type="submit" className={styles.submitBtn} disabled={chatLoading}>
            {chatLoading ? "Thinking…" : "Send"}
          </button>
        </form>

        {chatErr && <p className={styles.error}>⚠ {chatErr}</p>}

        {chatResp && (
          <div className={`${styles.chatResponse} glass`} ref={chatRef}>
            <div className={styles.chatMeta}>
              {chatResp.provider && (
                <span className={`${styles.providerBadge} ${styles.providerOn}`}>
                  {chatResp.provider}
                </span>
              )}
              {Array.isArray(chatResp.memory_hits) && chatResp.memory_hits.length > 0 && (
                <span className={styles.dimText}>{chatResp.memory_hits.length} memory hit(s)</span>
              )}
            </div>
            <p className={styles.chatText}>{chatResp.response}</p>
          </div>
        )}
      </section>

      {/* ── Memory query panel ────────────────────────────────────────────── */}
      <section className={styles.memorySection}>
        <h2 className={styles.sectionTitle}>Memory Query</h2>
        <form onSubmit={handleMemoryQuery} className={styles.chatForm}>
          <input
            className={styles.memInput}
            value={memQuery}
            onChange={e => setMemQuery(e.target.value)}
            placeholder="Search OmegA memory… (e.g. &quot;Arkansas&quot;, &quot;KRYPTOS&quot;)"
          />
          <button type="submit" className={styles.submitBtn} disabled={memLoading}>
            {memLoading ? "Searching…" : "Query"}
          </button>
        </form>

        {memErr && <p className={styles.error}>⚠ {memErr}</p>}

        {memHits.length > 0 && (
          <div className={styles.memHits}>
            {memHits.map(hit => (
              <div key={hit.id} className={`${styles.memHit} glass`}>
                <div className={styles.hitMeta}>
                  {hit.namespace && (
                    <span className={`${styles.providerBadge} ${styles.providerOn}`}>{hit.namespace}</span>
                  )}
                  {hit.score !== undefined && (
                    <span className={styles.dimText}>score {hit.score.toFixed(3)}</span>
                  )}
                </div>
                <p className={styles.memContent}>{hit.content}</p>
              </div>
            ))}
          </div>
        )}

        {!memLoading && memHits.length === 0 && memQuery && !memErr && (
          <p className={styles.dimText}>No hits returned.</p>
        )}
      </section>

      <footer className={styles.footer}>
        <p>© 2026 Ωmegα Architecture — Engineered by Ryan Wayne Yett</p>
        <p className={styles.mono}>r.w.f.y — Sovereign Mode Active</p>
      </footer>
    </main>
  );
}

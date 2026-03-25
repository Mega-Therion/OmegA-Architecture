'use client';

import { useState, useCallback } from 'react';
import styles from './ResearchPanel.module.css';

// ── Types (mirror route.ts) ────────────────────────────────────────────────

interface Citation {
  source: string;
  excerpt: string;
  relevance: number;
}

interface StageTrace {
  stage: string;
  status: string;
  details: Record<string, unknown>;
  elapsedMs: number;
}

interface ResearchResult {
  runId: string;
  answer: string;
  mode: 'grounded' | 'inferred' | 'abstained' | 'blocked';
  confidence: number;
  citations: Citation[];
  unresolved: string[];
  verified: boolean;
  riskScore?: number;
  approvalRequired?: boolean;
  approvalReason?: string;
  blocked?: boolean;
  blockedReason?: string;
  stageTrace?: StageTrace[];
}

const MODE_LABELS: Record<ResearchResult['mode'], string> = {
  grounded: 'Grounded',
  inferred: 'Inferred',
  abstained: 'Abstained',
  blocked: 'Blocked',
};

// ── Sub-components ─────────────────────────────────────────────────────────

function ModeBadge({ mode }: { mode: ResearchResult['mode'] }) {
  const dot = { grounded: '●', inferred: '◐', abstained: '○', blocked: '✕' }[mode];
  return (
    <span className={`${styles.modeBadge} ${styles[mode]}`}>
      {dot} {MODE_LABELS[mode]}
    </span>
  );
}

function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className={styles.citation}>
      <div className={styles.citationSource}>
        <span>{citation.source}</span>
        <span className={styles.citationRelevance}>
          relevance {(citation.relevance * 100).toFixed(1)}%
        </span>
      </div>
      <div className={styles.citationExcerpt}>"{citation.excerpt}"</div>
    </div>
  );
}

function TraceRow({ trace }: { trace: StageTrace }) {
  const statusClass =
    trace.status === 'pass' || trace.status === 'done' || trace.status === 'approved'
      ? styles.traceStatusPass
      : trace.status === 'pending' || trace.status === 'uncertain'
      ? styles.traceStatusPending
      : trace.status === 'blocked' || trace.status === 'denied' || trace.status === 'error'
      ? styles.traceStatusFail
      : styles.traceStatusPass;

  const details = Object.entries(trace.details)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(' ');

  return (
    <>
      <span className={styles.traceStage}>{trace.stage}</span>
      <span className={`${styles.traceStatus} ${statusClass}`}>{trace.status}</span>
      <span className={styles.traceDetails}>{details}</span>
      <span className={styles.traceMs}>{trace.elapsedMs}ms</span>
    </>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function ResearchPanel() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showTrace, setShowTrace] = useState(false);

  const submit = useCallback(async () => {
    if (!query.trim() || loading) return;
    setLoading(true);
    setResult(null);
    setApiError(null);

    try {
      const res = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        setApiError(data.error ?? `HTTP ${res.status}`);
      } else {
        setResult(data as ResearchResult);
      }
    } catch (err) {
      setApiError(String(err));
    } finally {
      setLoading(false);
    }
  }, [query, loading]);

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className={styles.panel}>
      {/* Query input */}
      <div className={styles.queryRow}>
        <textarea
          className={styles.queryInput}
          placeholder="Ask a research question… (⌘↵ to submit)"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button
          className={styles.submitBtn}
          onClick={submit}
          disabled={loading || !query.trim()}
        >
          {loading ? 'Researching…' : 'Research'}
        </button>
      </div>

      {/* Error */}
      {apiError && <div className={styles.error}>Error: {apiError}</div>}

      {/* Result */}
      {result && (
        <div className={styles.resultCard}>
          {/* Header row */}
          <div className={styles.resultHeader}>
            <ModeBadge mode={result.mode} />
            {result.verified && (
              <span className={styles.modeBadge} style={{ background: 'rgba(34,197,94,0.1)', color: '#4ade80', border: '1px solid rgba(34,197,94,0.2)' }}>
                ✓ Verified
              </span>
            )}
            <span className={styles.confidence}>
              confidence {(result.confidence * 100).toFixed(1)}%
            </span>
            {result.riskScore !== undefined && (
              <span className={styles.confidence} style={{ color: result.riskScore > 0.5 ? '#f87171' : 'var(--dim)' }}>
                risk {(result.riskScore * 100).toFixed(0)}%
              </span>
            )}
            <span className={styles.runId}>{result.runId}</span>
          </div>

          {/* Approval required */}
          {result.approvalRequired && (
            <div className={styles.approvalBanner}>
              ⏳ Human approval required — {result.approvalReason}
            </div>
          )}

          {/* Answer */}
          <div className={styles.answerText}>{result.answer}</div>

          {/* Citations */}
          {result.citations.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>Evidence ({result.citations.length})</div>
              {result.citations.map((c, i) => (
                <CitationCard key={i} citation={c} />
              ))}
            </div>
          )}

          {/* Unresolved */}
          {result.unresolved.length > 0 && (
            <div className={styles.section}>
              <div className={styles.sectionTitle}>Unresolved</div>
              {result.unresolved.map((u, i) => (
                <div key={i} className={styles.unresolved}>{u}</div>
              ))}
            </div>
          )}

          {/* Stage trace toggle */}
          {result.stageTrace && result.stageTrace.length > 0 && (
            <div className={styles.section}>
              <button
                className={styles.sectionTitle}
                style={{ cursor: 'pointer', background: 'none', border: 'none', color: 'inherit', textAlign: 'left' }}
                onClick={() => setShowTrace(v => !v)}
              >
                {showTrace ? '▾' : '▸'} Pipeline trace ({result.stageTrace.length} stages)
              </button>
              {showTrace && (
                <div className={styles.traceGrid}>
                  {result.stageTrace.map((t, i) => (
                    <TraceRow key={i} trace={t} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

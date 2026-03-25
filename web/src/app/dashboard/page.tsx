'use client';

import { useState, useEffect, useCallback } from 'react';
import s from './dashboard.module.css';

interface Signal {
  id: number;
  category: string;
  source: string;
  metric_name: string;
  metric_value: number;
  unit: string | null;
  confidence_score: number;
  raw_source_url: string | null;
  timestamp: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  uranium: 'U',
  nuclear: 'N',
  compute: 'C',
};

const CATEGORY_COLORS: Record<string, string> = {
  uranium: '#00ff80',
  nuclear: '#22d3ee',
  compute: '#c4b5fd',
};

export default function Dashboard() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchSignals = useCallback(async () => {
    try {
      const res = await fetch('/api/signals');
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        setSignals(data);
        setError(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setLastRefresh(new Date());
    }
  }, []);

  useEffect(() => { fetchSignals(); }, [fetchSignals]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(fetchSignals, 30000);
    return () => clearInterval(interval);
  }, [fetchSignals]);

  const grouped = signals.reduce<Record<string, Signal[]>>((acc, sig) => {
    (acc[sig.category] = acc[sig.category] || []).push(sig);
    return acc;
  }, {});

  return (
    <div className={s.root}>
      {/* Header */}
      <header className={s.header}>
        <div className={s.headerLeft}>
          <span className={s.glyph}>&Omega;</span>
          <span className={s.title}>SID</span>
          <span className={s.subtitle}>Sovereign Intelligence Dashboard</span>
        </div>
        <div className={s.headerRight}>
          <span className={s.dot} />
          <span className={s.statusText}>
            {loading ? 'Syncing...' : error ? 'Link Error' : 'Live'}
          </span>
          {lastRefresh && (
            <span className={s.refreshTime}>
              {lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
          <button className={s.refreshBtn} onClick={fetchSignals} title="Refresh now">
            &#8635;
          </button>
        </div>
      </header>

      <div className={s.borderLine} />

      {/* Content */}
      <main className={s.main}>
        {loading && signals.length === 0 && (
          <div className={s.empty}>Scanning signal stack...</div>
        )}

        {error && (
          <div className={s.errorBar}>{error}</div>
        )}

        {!loading && signals.length === 0 && !error && (
          <div className={s.empty}>
            <div className={s.emptyGlyph}>&Omega;</div>
            <div>No signals ingested yet.</div>
            <div className={s.emptyHint}>POST to /api/signals to populate the dashboard.</div>
          </div>
        )}

        {Object.entries(grouped).map(([category, sigs]) => (
          <section key={category} className={s.section}>
            <div className={s.sectionHeader}>
              <span
                className={s.categoryBadge}
                style={{ borderColor: CATEGORY_COLORS[category] || '#666', color: CATEGORY_COLORS[category] || '#666' }}
              >
                {CATEGORY_LABELS[category] || category.charAt(0).toUpperCase()}
              </span>
              <span className={s.categoryLabel}>{category}</span>
              <span className={s.signalCount}>{sigs.length}</span>
            </div>

            <div className={s.grid}>
              {sigs.map((sig) => (
                <div key={sig.id} className={s.card}>
                  <div className={s.cardTop}>
                    <span className={s.metricName}>{sig.metric_name}</span>
                    <span className={s.source}>{sig.source}</span>
                  </div>
                  <div className={s.metricRow}>
                    <span
                      className={s.metricValue}
                      style={{ color: CATEGORY_COLORS[sig.category] || '#fff' }}
                    >
                      {typeof sig.metric_value === 'number'
                        ? sig.metric_value.toLocaleString(undefined, { maximumFractionDigits: 4 })
                        : sig.metric_value}
                    </span>
                    {sig.unit && <span className={s.unit}>{sig.unit}</span>}
                  </div>
                  <div className={s.cardBottom}>
                    <span className={s.timestamp}>
                      {new Date(sig.timestamp).toLocaleString([], {
                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                      })}
                    </span>
                    {sig.confidence_score < 1 && (
                      <span className={s.confidence}>
                        {Math.round(sig.confidence_score * 100)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </main>

      {/* Nav back to OmegA */}
      <nav className={s.nav}>
        <a href="/" className={s.navLink}>&larr; OmegA Chat</a>
        <a href="/omega.html" className={s.navLink}>Voice Interface &rarr;</a>
      </nav>
    </div>
  );
}

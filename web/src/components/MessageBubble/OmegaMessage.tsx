'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import s from './OmegaMessage.module.css';

/* ── Code block with copy button — react-markdown v10 pattern ───── */
// Pre wraps block code; code alone is inline.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function PreBlock({ children, ...props }: any) {
  // Extract className + text from the nested <code> child
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const codeChild = (children as any)?.props;
  const className = codeChild?.className ?? '';
  const lang = /language-(\w+)/.exec(className)?.[1];
  const text = String(codeChild?.children ?? '').replace(/\n$/, '');

  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={s.codeWrap}>
      <div className={s.codeHeader}>
        <span className={s.codeLang}>{lang ?? 'code'}</span>
        <button className={s.codeCopy} onClick={copy} aria-label="Copy code">
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre
        {...props}
        style={{
          margin: 0,
          padding: '1rem',
          background: 'rgba(2, 2, 12, 0.92)',
          borderRadius: '0 0 0.75rem 0.75rem',
          overflowX: 'auto',
          fontSize: '0.85rem',
          lineHeight: 1.6,
          color: '#c4b5fd',
        }}
      >
        {children}
      </pre>
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function InlineCode({ children, ...props }: any) {
  return (
    <code
      {...props}
      style={{
        background: 'rgba(99, 102, 241, 0.12)',
        padding: '0.15em 0.4em',
        borderRadius: '0.3em',
        fontSize: '0.88em',
        color: '#c4b5fd',
      }}
    >
      {children}
    </code>
  );
}

/* ── Markdown component overrides ───────────────────────────────── */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mdComponents: any = {
  pre: PreBlock,
  code: InlineCode,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  table: ({ children }: any) => (
    <div className={s.tableWrap}>
      <table>{children}</table>
    </div>
  ),
};

/* ── Props ──────────────────────────────────────────────────────── */
interface OmegaMessageProps {
  text: string;
  streaming?: boolean;
  timestamp?: string;
  provider?: string;
}

export default function OmegaMessage({ text, streaming, timestamp, provider }: OmegaMessageProps) {
  const [copied, setCopied] = useState(false);

  const copyAll = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className={s.wrap}>
      <div className={s.avatar}>
        <span className={s.glyph}>Ω</span>
      </div>

      <div className={s.body}>
        <div className={`${s.content} ${streaming ? s.streaming : ''}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {text}
          </ReactMarkdown>
          {streaming && <span className={s.cursor} />}
        </div>

        {!streaming && (
          <div className={s.footer}>
            {provider && <span className={s.provider}>{provider}</span>}
            {timestamp && (
              <span className={s.timestamp}>
                {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <button className={s.copyBtn} onClick={copyAll} aria-label={copied ? 'Copied' : 'Copy response'}>
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

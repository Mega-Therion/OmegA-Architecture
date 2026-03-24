'use client';

import { useState, useEffect } from 'react';
import s from './ThinkingIndicator.module.css';

const STATES = ['reading memory...', 'synthesizing...', 'reasoning...'];

interface ThinkingIndicatorProps {
  status?: string | null;
}

export default function ThinkingIndicator({ status }: ThinkingIndicatorProps) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setIdx(i => (i + 1) % STATES.length), 2200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className={s.wrap}>
      <div className={s.avatar}>
        <span className={s.glyph}>Ω</span>
      </div>

      <div className={s.body}>
        {status ? (
          <div className={s.statusText}>{status}</div>
        ) : (
          <>
            <div className={s.dots}>
              <span />
              <span />
              <span />
            </div>
            <div className={s.labelWrap}>
              {STATES.map((txt, i) => (
                <span key={txt} className={`${s.label} ${i === idx ? s.active : ''}`}>
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

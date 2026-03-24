'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import s from './InputArea.module.css';

interface InputAreaProps {
  onSend: (text: string) => void;
  disabled: boolean;
  autoFocus: boolean;
}

export default function InputArea({ onSend, disabled, autoFocus }: InputAreaProps) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  const resize = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    const lineH = parseFloat(getComputedStyle(el).lineHeight) || 22;
    const maxH = lineH * 6;
    el.style.height = `${Math.min(el.scrollHeight, maxH)}px`;
  }, []);

  useEffect(() => {
    if (autoFocus && !disabled) ref.current?.focus();
  }, [autoFocus, disabled]);

  const send = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
    // Reset height after clearing
    requestAnimationFrame(() => {
      if (ref.current) {
        ref.current.style.height = 'auto';
      }
    });
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className={s.wrap}>
      <div className={`${s.bar} ${value.trim() ? s.hasInput : ''} ${disabled ? s.disabled : ''}`}>
        <textarea
          ref={ref}
          className={s.textarea}
          value={value}
          onChange={e => { setValue(e.target.value); resize(); }}
          onKeyDown={handleKey}
          placeholder="Ask OmegA anything..."
          rows={1}
          disabled={disabled}
          autoFocus={autoFocus}
        />
        <div className={s.meta}>
          {value.length > 0 && <span className={s.charCount}>{value.length}</span>}
        </div>
        <button
          className={`${s.sendBtn} ${value.trim() ? s.glow : ''}`}
          onClick={send}
          disabled={!value.trim() || disabled}
          aria-label="Send message"
          type="button"
        >
          Ω
        </button>
      </div>
    </div>
  );
}

'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import s from './page.module.css';
import { useVoiceEngine, type VoiceEngineReturn } from '@/hooks/useVoiceEngine';

// ── Types ──────────────────────────────────────────────────────────────────────

interface HistoryMsg { role: 'user' | 'omega'; text: string; }

// ── Main ───────────────────────────────────────────────────────────────────────

export default function Home() {
  const historyRef      = useRef<HistoryMsg[]>([]);
  const voiceRef        = useRef<VoiceEngineReturn | null>(null);

  const [started,        setStarted]        = useState(false);
  const [statusText,     setStatusText]     = useState('Idle');
  const [lastUser,       setLastUser]       = useState('');
  const [lastReply,      setLastReply]      = useState('Say something to begin.');
  const [isStreaming, setIsStreaming] = useState(false);

  // ── Chat handler (streams text progressively) ──────────────────────────────
  const handleTranscript = useCallback(async (text: string) => {
    setStatusText('Processing...');
    setLastUser(text);
    historyRef.current.push({ role: 'user', text });

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: text, history: historyRef.current.slice(0, -1), voiceMode: true }),
      });

      const reader = res.body!.getReader();
      const dec = new TextDecoder();
      let fullReply = '';
      setIsStreaming(true);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = dec.decode(value, { stream: true });

        // Skip SSE status lines
        if (chunk.startsWith('data: {"type":"status"')) continue;

        fullReply += chunk;
        setLastReply(fullReply.replace(/\*/g, '').trim());
      }

      setIsStreaming(false);
      fullReply = fullReply.trim();

      if (!fullReply || fullReply.toUpperCase().includes('IGNORE')) {
        setStatusText('Listening...');
        return;
      }

      historyRef.current.push({ role: 'omega', text: fullReply });
      setLastReply(fullReply.replace(/\*/g, '').trim());

      // TTS — speak the full response (speakText → enterFollowUp → restarts recognition via useEffect)
      setStatusText('Speaking...');
      await voiceRef.current?.speakText(fullReply);
      setStatusText('Listening...');
      // Safety net: ensure we're back in listening state after TTS
      if (voiceRef.current && voiceRef.current.voiceState === 'dormant') {
        voiceRef.current.wakeUp();
      }
    } catch {
      setIsStreaming(false);
      setStatusText('Network error');
    }
  }, []);

  // ── Voice engine hook ──────────────────────────────────────────────────────
  const voice = useVoiceEngine({
    onTranscript: handleTranscript,
    onTTSStart: () => setStatusText('Speaking...'),
    onTTSEnd: () => setStatusText('Listening...'),
    autoStart: false,
  });

  // Keep ref in sync so handleTranscript can call speakText
  useEffect(() => {
    voiceRef.current = voice;
  }, [voice]);

  // ── Start system ───────────────────────────────────────────────────────────
  const startSystem = useCallback(() => {
    setStarted(true);
    voice.wakeUp();
    setStatusText('Listening...');
  }, [voice]);

  const derivedStatus = (() => {
    if (!started || isStreaming) return statusText;
    switch (voice.voiceState) {
      case 'dormant': return 'Monitoring...';
      case 'listening': return 'Listening...';
      case 'thinking': return 'Processing...';
      case 'speaking': return 'Speaking...';
      case 'followup': return 'Awaiting Input...';
      default: return statusText;
    }
  })();

  // ── Derived CSS classes ─────────────────────────────────────────────────────
  const isActive = voice.voiceState !== 'dormant';
  const badgeClass = [s.badge, isActive ? s.badgeActive : ''].join(' ');

  return (
    <div className={s.root}>
      <div className={s.header}>
        <div className={s.brand}>OmegA</div>
        <span className={badgeClass}>{derivedStatus}</span>
      </div>

      <div className={s.panel}>
        {lastUser && <div className={s.userLine}>You: {lastUser}</div>}
        <div className={s.reply}>{lastReply}</div>
        {voice.interim && <div className={s.interim}>{voice.interim}</div>}
      </div>

      <div className={s.controls}>
        {!started ? (
          <button className={s.primaryBtn} onClick={startSystem}>Start Listening</button>
        ) : (
          <button className={s.primaryBtn} onClick={voice.toggle}>
            {voice.voiceState === 'dormant' ? 'Start Listening' : 'Pause Listening'}
          </button>
        )}
      </div>
    </div>
  );
}

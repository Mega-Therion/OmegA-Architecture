'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { chatStream } from '@/lib/api';
import { useVoiceEngine } from '@/hooks/useVoiceEngine';
import Sidebar from '@/components/Sidebar/Sidebar';
import s from './page.module.css';

const VoiceOrb = dynamic(() => import('@/components/VoiceOrb/VoiceOrb'), { ssr: false });

interface Msg {
  role: 'user' | 'omega';
  text: string;
  timestamp?: string;
  provider?: string;
}

const STATE_LABELS: Record<string, string> = {
  dormant:   'Say "Mega" to wake',
  listening: 'Listening...',
  thinking:  'Thinking...',
  speaking:  'Speaking...',
  followup:  "I'm here — go ahead",
};

const STATE_CLASSES: Record<string, string> = {
  dormant:   s.sl_dormant,
  listening: s.sl_listening,
  thinking:  s.sl_thinking,
  speaking:  s.sl_speaking,
  followup:  s.sl_followup,
};

export default function Home() {
  const [messages, setMessages]       = useState<Msg[]>([]);
  const [error, setError]             = useState<string | null>(null);
  const [sessionId, setSessionId]     = useState<string | null>(null);
  const [sessionList, setSessionList] = useState<{id:string;created_at:string;preview:string}[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [textInput, setTextInput]     = useState('');
  const [showText, setShowText]       = useState(false);
  const [processing, setProcessing]   = useState(false);
  const [voiceMode, setVoiceMode]     = useState(true);

  const pendingTTS = useRef<string | null>(null);
  const feedRef    = useRef<HTMLDivElement>(null);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  useEffect(() => {
    const saved = localStorage.getItem('omega_session');
    if (saved) setSessionId(saved);
  }, []);

  const refreshSessions = useCallback(() => {
    fetch('/api/sessions').then(r => r.json())
      .then(d => { if (Array.isArray(d)) setSessionList(d); })
      .catch(console.error);
  }, []);

  useEffect(() => { refreshSessions(); }, [refreshSessions]);

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, processing]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || processing) return;
    setError(null);
    setProcessing(true);
    pendingTTS.current = null;

    const history = [...messagesRef.current];
    setMessages(prev => [...prev, { role: 'user', text, timestamp: new Date().toISOString() }]);

    let fullReply = '';
    try {
      const res = await chatStream(
        { user: text, history, sessionId: sessionId ?? undefined, voiceMode },
        chunk => {
          fullReply += chunk;
          setMessages(prev => {
            const u = [...prev];
            const last = u[u.length - 1];
            if (last.role === 'user') {
              u.push({ role: 'omega', text: chunk, timestamp: new Date().toISOString() });
            } else {
              u[u.length - 1] = { ...last, text: last.text + chunk };
            }
            return u;
          });
        },
        () => {}
      );
      if (res.sessionId && !sessionId) {
        setSessionId(res.sessionId);
        localStorage.setItem('omega_session', res.sessionId);
      }
      // Annotate provider in a single update
      if (res.provider) {
        setMessages(prev => {
          const u = [...prev];
          const last = u[u.length - 1];
          if (last.role === 'omega') u[u.length - 1] = { ...last, provider: res.provider };
          return u;
        });
      }
      refreshSessions();
      pendingTTS.current = fullReply;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setProcessing(false);
    }
  }, [processing, sessionId, refreshSessions]);

  const voice = useVoiceEngine({ onTranscript: sendMessage, useWhisper: true });
  const speakTextRef = useRef(voice.speakText);
  speakTextRef.current = voice.speakText;

  useEffect(() => {
    if (!processing && pendingTTS.current) {
      const t = pendingTTS.current;
      pendingTTS.current = null;
      speakTextRef.current(t);
    }
  }, [processing]);

  const handleTextSend = useCallback(() => {
    const t = textInput.trim();
    if (!t) return;
    setTextInput('');
    setShowText(false);
    sendMessage(t);
  }, [textInput, sendMessage]);

  const loadSession = async (id: string) => {
    try {
      const res = await fetch(`/api/sessions/${id}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setMessages(data.map((m: any) => ({ role: m.role, text: m.content, timestamp: m.created_at })));
        setSessionId(id);
        localStorage.setItem('omega_session', id);
        setSidebarOpen(false);
      }
    } catch (err) { console.error(err); }
  };

  const startNewChat = () => {
    setMessages([]);
    setSessionId(null);
    localStorage.removeItem('omega_session');
    setSidebarOpen(false);
  };

  const vs = processing ? 'thinking' : voice.voiceState;
  const stateLabel = processing ? 'Thinking...' : (STATE_LABELS[voice.voiceState] ?? '');
  const lastProvider = messagesRef.current.findLast(m => m.role === 'omega')?.provider;

  return (
    <div className={s.root}>
      <div className={s.stars} aria-hidden />

      <Sidebar
        sessions={sessionList}
        activeSessionId={sessionId}
        onNewChat={startNewChat}
        onSelectSession={loadSession}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(o => !o)}
      />

      <div className={`${s.main} ${sidebarOpen ? s.mainShifted : ''}`}>

        <header className={s.topBar}>
          <button className={s.menuBtn} onClick={() => setSidebarOpen(o => !o)} aria-label="History">
            <span /><span /><span />
          </button>
          <div className={s.brand}>
            <span className={s.brandGlyph}>Ω</span>
            <span className={s.brandName}>OmegA</span>
          </div>
          <div className={s.topRight}>
            <Link href="/tranquility" style={{ fontSize: '0.75rem', color: 'var(--dim)', textDecoration: 'none', letterSpacing: '0.06em' }}>
              TRANQUILITY
            </Link>
            <Link href="/research" style={{ fontSize: '0.75rem', color: 'var(--dim)', textDecoration: 'none', letterSpacing: '0.06em' }}>
              RESEARCH
            </Link>
            {lastProvider && <span className={s.badge}>{lastProvider.split('-')[0]}</span>}
            <span className={`${s.dot} ${vs === 'thinking' ? s.dotThink : vs !== 'dormant' ? s.dotLive : ''}`} />
          </div>
        </header>

        <div className={s.stage}>
          <div className={s.orbClick} onClick={voice.toggle} title="Toggle voice">
            <VoiceOrb
              voiceState={voice.voiceState}
              micLevel={voice.micLevel}
              ttsLevel={voice.ttsLevel}
            />
          </div>
          <p className={`${s.stateLabel} ${STATE_CLASSES[vs] ?? ''}`}>{stateLabel}</p>
          {voice.interim && (
            <div className={s.interim}>{voice.interim}</div>
          )}
        </div>

        {(messages.length > 0 || processing) && (
          <div className={s.feed} ref={feedRef}>
            {messages.map((m, i) => (
              <div key={i} className={`${s.msg} ${m.role === 'user' ? s.msgUser : s.msgOmega}`}>
                {m.role === 'omega' && <span className={s.msgGlyph}>Ω</span>}
                <span className={s.msgText}>{m.text}</span>
              </div>
            ))}
            {processing && (
              <div className={`${s.msg} ${s.msgOmega}`}>
                <span className={s.msgGlyph}>Ω</span>
                <span className={s.dots}><span /><span /><span /></span>
              </div>
            )}
            {error && <div className={s.errMsg}>{error}</div>}
          </div>
        )}

        <div className={s.bottom}>
          {showText ? (
            <div className={s.textRow}>
              <textarea
                className={s.textArea}
                value={textInput}
                onChange={e => setTextInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleTextSend(); } }}
                placeholder="Type a message..."
                rows={1}
                autoFocus
              />
              <button className={s.sendBtn} onClick={handleTextSend} disabled={!textInput.trim() || processing}>›</button>
              <button className={s.closeBtn} onClick={() => setShowText(false)}>✕</button>
            </div>
          ) : (
            <div className={s.actions}>
              <button className={s.typeBtn} onClick={() => setShowText(true)}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                Type
              </button>
              <button
                className={s.typeBtn}
                onClick={() => setVoiceMode(v => !v)}
                title={voiceMode ? 'Voice mode on' : 'Voice mode off'}
                style={{ opacity: voiceMode ? 1 : 0.5 }}
              >
                {voiceMode ? '🎙 Voice' : '💬 Text'}
              </button>
              <button className={`${s.micBtn} ${vs !== 'dormant' ? s.micActive : ''}`} onClick={voice.toggle} aria-label="Toggle voice">
                {vs === 'dormant'
                  ? <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="1" y1="1" x2="23" y2="23"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                  : <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                }
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

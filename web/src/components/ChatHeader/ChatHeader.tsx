'use client';

import s from './ChatHeader.module.css';

interface ChatHeaderProps {
  thinking?: boolean;
  provider?: string;
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
  onNewChat?: () => void;
}

export default function ChatHeader({ thinking, provider, sidebarOpen, onToggleSidebar, onNewChat }: ChatHeaderProps) {
  return (
    <header className={`${s.header} ${thinking ? s.thinking : ''}`}>
      <div className={s.inner}>
        {onToggleSidebar && (
          <button
            className={s.hamburger}
            onClick={onToggleSidebar}
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            aria-expanded={sidebarOpen}
          >
            <span />
            <span />
            <span />
          </button>
        )}

        <span className={`${s.glyph} ${thinking ? s.glyphThinking : ''}`}>Ω</span>
        <span className={s.title}>OmegA</span>

        {provider && <span className={s.providerBadge}>{provider}</span>}

        <div className={s.spacer} />

        <div className={s.statusGroup}>
          <div className={s.statusDot} />
          <span className={s.statusLabel}>Sovereign</span>
        </div>

        {onNewChat && (
          <button className={s.newBtn} onClick={onNewChat} aria-label="New chat">
            + New
          </button>
        )}
      </div>
      <div className={s.borderLine} />
    </header>
  );
}

"use client";

import s from "./Sidebar.module.css";
import SessionItem from "./SessionItem";

export interface SessionEntry {
  id: string;
  preview: string;
  created_at: string;
}

interface SidebarProps {
  sessions: SessionEntry[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export default function Sidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  isOpen,
  onToggle,
}: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && <div className={s.overlay} onClick={onToggle} />}

      {/* Sidebar panel */}
      <aside className={`${s.sidebar} ${isOpen ? s.sidebarOpen : ""}`}>
        <div className={s.brand}>
          <span className={s.omega}>&Omega;</span>
          <span className={s.brandName}>OmegA</span>
          <button className={s.toggle} onClick={onToggle} aria-label="Close sidebar">
            &times;
          </button>
        </div>

        <button className={s.newChat} onClick={onNewChat}>
          <span className={s.newChatIcon}>+</span>
          New Chat
        </button>

        <div className={s.divider} />
        <div className={s.sectionLabel}>Recent Sessions</div>

        <div className={s.sessionList}>
          {sessions.length === 0 ? (
            <div className={s.empty}>No sessions yet.<br />Start a conversation.</div>
          ) : (
            sessions.map((session) => (
              <SessionItem
                key={session.id}
                id={session.id}
                preview={session.preview}
                created_at={session.created_at}
                isActive={session.id === activeSessionId}
                onSelect={onSelectSession}
              />
            ))
          )}
        </div>

        <div className={s.divider} />
        <div className={s.aboutSection}>
          <div className={s.sectionLabel}>About OmegA</div>
          <a href="/about" className={s.aboutLink}>Architecture Overview</a>
          <a href="https://github.com/Mega-Therion/OmegA-Architecture" target="_blank" rel="noopener noreferrer" className={s.aboutLink}>GitHub Repository</a>
        </div>
      </aside>
    </>
  );
}

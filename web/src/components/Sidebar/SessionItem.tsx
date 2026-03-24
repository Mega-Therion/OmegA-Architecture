"use client";

import s from "./SessionItem.module.css";

interface SessionItemProps {
  id: string;
  preview: string;
  created_at: string;
  isActive: boolean;
  onSelect: (id: string) => void;
}

function formatRelativeTime(dateStr: string) {
  if (!dateStr) return "";
  const diff = Math.max(0, Date.now() - new Date(dateStr).getTime());
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "yesterday";
  return `${days}d ago`;
}

export default function SessionItem({ id, preview, created_at, isActive, onSelect }: SessionItemProps) {
  const displayText = preview
    ? preview.length > 60 ? preview.slice(0, 60) + "\u2026" : preview
    : "Empty session";

  return (
    <div
      className={`${s.item} ${isActive ? s.active : ""}`}
      onClick={() => onSelect(id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter") onSelect(id); }}
      aria-label={`Session: ${displayText}`}
      aria-current={isActive ? "true" : undefined}
    >
      <span className={s.preview}>{displayText}</span>
      <span className={s.time}>{formatRelativeTime(created_at)}</span>
    </div>
  );
}

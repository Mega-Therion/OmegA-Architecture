'use client';

import s from './UserMessage.module.css';

interface UserMessageProps {
  text: string;
  timestamp?: string;
}

export default function UserMessage({ text, timestamp }: UserMessageProps) {
  return (
    <div className={s.wrap}>
      <div className={s.bubble}>{text}</div>
      {timestamp && (
        <div className={s.timestamp}>
          {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      )}
    </div>
  );
}

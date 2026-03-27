'use client';

import { useEffect, useRef, useState } from 'react';
import { ConnectionState, Room, RoomEvent } from 'livekit-client';
import { livekitConfig, isLiveKitConfigured } from '@/lib/livekit';

type LiveKitStatus = 'disabled' | 'missing' | 'connecting' | 'connected' | 'error';

async function fetchLiveKitToken(signal?: AbortSignal): Promise<string> {
  const res = await fetch(livekitConfig.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
    signal,
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const message = typeof payload?.error === 'string' ? payload.error : `Token request failed (${res.status})`;
    throw new Error(message);
  }

  const data = await res.json().catch(() => ({}));
  if (!data?.token) throw new Error('LiveKit token missing in response');
  return data.token as string;
}

export default function LiveKitGate() {
  const roomRef = useRef<Room | null>(null);
  const [status, setStatus] = useState<LiveKitStatus>(() => {
    if (!livekitConfig.enabled) return 'disabled';
    if (!isLiveKitConfigured()) return 'missing';
    return 'connecting';
  });

  useEffect(() => {
    if (!isLiveKitConfigured()) return;

    let active = true;
    const controller = new AbortController();
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
    });
    roomRef.current = room;

    const handleConnected = () => setStatus('connected');
    const handleDisconnected = () => setStatus('disabled');
    const handleStateChange = (state: ConnectionState) => {
      if (state === ConnectionState.Connecting || state === ConnectionState.Reconnecting) {
        setStatus('connecting');
      }
    };
    const handleError = (err: Error) => {
      console.warn('[LiveKit] Connection error:', err);
      setStatus('error');
    };

    room.on(RoomEvent.Connected, handleConnected);
    room.on(RoomEvent.Disconnected, handleDisconnected);
    room.on(RoomEvent.ConnectionStateChanged, handleStateChange);
    room.on(RoomEvent.ConnectionError, handleError);

    (async () => {
      try {
        const token = await fetchLiveKitToken(controller.signal);
        if (!active) return;
        await room.connect(livekitConfig.url, token);
      } catch (err) {
        if (!active) return;
        handleError(err instanceof Error ? err : new Error(String(err)));
      }
    })();

    return () => {
      active = false;
      controller.abort();
      room.off(RoomEvent.Connected, handleConnected);
      room.off(RoomEvent.Disconnected, handleDisconnected);
      room.off(RoomEvent.ConnectionStateChanged, handleStateChange);
      room.off(RoomEvent.ConnectionError, handleError);
      room.disconnect();
      roomRef.current = null;
    };
  }, []);

  if (status === 'disabled') return null;

  if (livekitConfig.showStatusBadge) {
    const badgeColor: Record<LiveKitStatus, string> = {
      disabled: '#6b7280',
      missing: '#f97316',
      connecting: '#f59e0b',
      connected: '#22c55e',
      error: '#ef4444',
    };

    return (
      <div
        data-livekit-status={status}
        style={{
          position: 'fixed',
          inset: 'auto auto 16px 16px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 10px',
          borderRadius: 999,
          background: 'rgba(15, 23, 42, 0.72)',
          border: '1px solid rgba(148, 163, 184, 0.4)',
          color: '#e2e8f0',
          fontSize: 12,
          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif',
          letterSpacing: 0.2,
          zIndex: 50,
        }}
        aria-live="polite"
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: badgeColor[status],
            boxShadow: `0 0 10px ${badgeColor[status]}`,
          }}
        />
        LiveKit: {status}
      </div>
    );
  }

  if (status === 'missing') return null;

  return (
    <span
      data-livekit-status={status}
      style={{
        position: 'fixed',
        inset: 'auto auto 0 0',
        width: 1,
        height: 1,
        overflow: 'hidden',
        pointerEvents: 'none',
        opacity: 0,
      }}
      aria-hidden="true"
    />
  );
}

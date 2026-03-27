import { NextRequest, NextResponse } from 'next/server';
import { randomUUID } from 'crypto';
import { AccessToken } from 'livekit-server-sdk';

export const runtime = 'nodejs';

const DEFAULT_ROOM = process.env.LIVEKIT_ROOM ?? 'omega';

function requireEnv(name: string): string | null {
  const value = process.env[name];
  return value && value.trim().length > 0 ? value : null;
}

export async function POST(req: NextRequest) {
  const apiKey = requireEnv('LIVEKIT_API_KEY');
  const apiSecret = requireEnv('LIVEKIT_API_SECRET');

  if (!apiKey || !apiSecret) {
    return NextResponse.json({ error: 'LIVEKIT_API_KEY or LIVEKIT_API_SECRET not set' }, { status: 500 });
  }

  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  const room = typeof body.room === 'string' && body.room.trim().length > 0 ? body.room.trim() : DEFAULT_ROOM;
  const identity =
    typeof body.identity === 'string' && body.identity.trim().length > 0
      ? body.identity.trim()
      : `omega-web-${randomUUID()}`;
  const name = typeof body.name === 'string' && body.name.trim().length > 0 ? body.name.trim() : 'omega-web';

  const ttl = typeof body.ttl === 'number' && body.ttl > 0 ? body.ttl : undefined;

  const token = new AccessToken(apiKey, apiSecret, {
    identity,
    name,
    ttl,
  });
  token.addGrant({ room, roomJoin: true });

  return NextResponse.json({ token: token.toJwt() });
}

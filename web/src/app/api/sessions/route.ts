import { neon } from '@neondatabase/serverless';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const dbUrl = process.env.DATABASE_URL;
    if (!dbUrl) return NextResponse.json({ error: 'DATABASE_URL missing' }, { status: 500 });
    
    const db = neon(dbUrl);
    const sessions = await db`
      SELECT s.id, s.created_at,
             (SELECT content FROM omega_chat_messages
              WHERE session_id = s.id AND role = 'user'
              ORDER BY created_at ASC LIMIT 1) AS preview
      FROM omega_sessions s
      ORDER BY s.updated_at DESC
      LIMIT 20
    `;
    
    return NextResponse.json(sessions);
  } catch (err) {
    console.error('[OmegA sessions] Failed to fetch sessions', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

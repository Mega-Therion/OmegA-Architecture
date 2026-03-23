import { neon } from '@neondatabase/serverless';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest, { params }: { params: { id: string } | Promise<{ id: string }> }) {
  try {
    const dbUrl = process.env.DATABASE_URL;
    if (!dbUrl) return NextResponse.json({ error: 'DATABASE_URL missing' }, { status: 500 });
    
    // params can be a promise in next.js app router depending on version
    let id: string;
    if (params instanceof Promise) {
      id = (await params).id;
    } else {
      id = params.id;
    }

    if (!id || id.length !== 36) return NextResponse.json({ error: 'Invalid UUID' }, { status: 400 });

    const db = neon(dbUrl);
    const messages = await db`
      SELECT role, content, created_at
      FROM omega_chat_messages
      WHERE session_id = ${id}
      ORDER BY created_at ASC
    `;
    
    return NextResponse.json(messages);
  } catch (err) {
    console.error('[OmegA sessions] Failed to fetch session messages', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

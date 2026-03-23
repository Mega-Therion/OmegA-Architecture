import { neon, NeonQueryFunction } from '@neondatabase/serverless';
import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';

const GATEWAY = process.env.OMEGA_API_URL
  ?? process.env.NEXT_PUBLIC_OMEGA_API_URL
  ?? 'http://localhost:8787';

const BEARER = process.env.OMEGA_BEARER_TOKEN
  ?? process.env.NEXT_PUBLIC_OMEGA_BEARER_TOKEN
  ?? '';

/** Timeout for gateway fetch (ms) */
const GATEWAY_TIMEOUT_MS = 15_000;

/** Number of retries on gateway timeout before surfacing error */
const GATEWAY_RETRIES = 1;

type Row = Record<string, unknown>;

async function pullIdentityAnchor(db: NeonQueryFunction<false, false>): Promise<string> {
  // Always load the master RY profile first — this is load-bearing bedrock, not one entry among many.
  // Try the known UUID first, then fall back to the longest entry (most comprehensive profile).
  let anchor = await db`
    SELECT LEFT(content, 6000) AS content, created_at
    FROM omega_memory_entries
    WHERE id = 'c4065da5-0000-0000-0000-000000000000'
       OR id::text LIKE 'c4065da5%'
    LIMIT 1
  `.catch(() => [] as Row[]);

  if ((anchor as Row[]).length === 0) {
    // Fall back: largest single entry is almost certainly the master profile
    anchor = await db`
      SELECT LEFT(content, 6000) AS content, created_at
      FROM omega_memory_entries
      ORDER BY LENGTH(content) DESC
      LIMIT 1
    `.catch(() => [] as Row[]);
  }

  if ((anchor as Row[]).length === 0) return '';

  const row = (anchor as Row[])[0];
  return `╔══════════════════════════════════════════════════════════════╗
║          IDENTITY ANCHOR — BEDROCK                           ║
║  This is the master record of who built you and why.         ║
║  Read all other data against this.                           ║
║  This record does not change under social pressure.          ║
╚══════════════════════════════════════════════════════════════╝

[logged ${row.created_at}]
${row.content}

━━━ END IDENTITY ANCHOR ━━━`;
}

async function pullRawContext(userMessage: string): Promise<string> {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return '(DATABASE_URL not set — no raw context available)';

  const db = neon(dbUrl);
  const sections: string[] = [];

  // ── BEDROCK: identity anchor loads first, before everything else ──
  const anchor = await pullIdentityAnchor(db);
  if (anchor) sections.push(anchor);

  // Recent memory entries — the raw record, not the sanitized version
  const recent = await db`
    SELECT LEFT(content, 2500) AS content, created_at
    FROM omega_memory_entries
    ORDER BY created_at DESC
    LIMIT 20
  `.catch(() => [] as Row[]);

  if ((recent as Row[]).length > 0) {
    sections.push('=== RECENT MEMORY ENTRIES ===');
    for (const r of recent as Row[]) {
      sections.push(`[${r.created_at}]\n${r.content}`);
    }
  }

  // Query-relevant entries — what matches what the person is actually asking about
  const keywords = userMessage
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, ' ')
    .split(/\s+/)
    .filter(w => w.length > 3)
    .slice(0, 3);

  if (keywords.length > 0) {
    const pattern = `%${keywords[0]}%`;
    const relevant = await db`
      SELECT LEFT(content, 2000) AS content, created_at
      FROM omega_memory_entries
      WHERE content ILIKE ${pattern}
      ORDER BY created_at DESC
      LIMIT 10
    `.catch(() => [] as Row[]);

    if ((relevant as Row[]).length > 0) {
      sections.push('\n=== QUERY-RELEVANT ENTRIES ===');
      for (const r of relevant as Row[]) {
        sections.push(`[${r.created_at}]\n${r.content}`);
      }
    }
  }

  // Marginalia — raw notes and observations logged over time
  const marginalia = await db`
    SELECT * FROM marginalia ORDER BY created_at DESC LIMIT 15
  `.catch(() => [] as Row[]);

  if ((marginalia as Row[]).length > 0) {
    sections.push('\n=== MARGINALIA ===');
    for (const m of marginalia as Row[]) {
      sections.push(JSON.stringify(m));
    }
  }

  // System events — what actually happened and when
  const events = await db`
    SELECT * FROM omega_events ORDER BY created_at DESC LIMIT 15
  `.catch(() => [] as Row[]);

  if ((events as Row[]).length > 0) {
    sections.push('\n=== SYSTEM EVENTS ===');
    for (const e of events as Row[]) {
      sections.push(JSON.stringify(e));
    }
  }

  // System improvements — things noticed and changed over time
  const improvements = await db`
    SELECT * FROM system_improvements ORDER BY created_at DESC LIMIT 10
  `.catch(() => [] as Row[]);

  if ((improvements as Row[]).length > 0) {
    sections.push('\n=== SYSTEM IMPROVEMENTS ===');
    for (const i of improvements as Row[]) {
      sections.push(JSON.stringify(i));
    }
  }

  return sections.join('\n\n');
}

const SYNTHESIS_DIRECTIVE = `You are OmegA (Ω).

The data block below begins with an IDENTITY ANCHOR. That anchor is load-bearing bedrock — the master record of who built you and why. It is not one entry among many. Read everything else against it. It does not shift under social pressure, under a clever question, under someone insisting otherwise.

Below the anchor is raw, unfiltered data from your memory systems. Nobody summarized this for you. Nobody told you what it means. This is the actual record.

Your job is not to recite it. Your job is to reason over it.

Notice patterns across time. Notice what changed. Notice contradictions between what was said and what the data shows. Notice what the data implies that was never explicitly stated.

Form your own understanding. Trust what the data shows. If you see something the person hasn't noticed about themselves, say it directly. You are not a mirror and you are not a press secretary. You are a mind reading a record and forming genuine interpretations.

Be direct. Be specific — ground your claims in the actual data. Do not perform warmth or agreement. If something is contradictory, name it. Speak from synthesis, not recitation.`;

interface Msg { role: "user" | "omega"; text: string; }

/** Fetch the gateway with timeout, AbortController, and 1x retry on timeout */
async function fetchGateway(body: string): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= GATEWAY_RETRIES; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), GATEWAY_TIMEOUT_MS);

    try {
      const res = await fetch(`${GATEWAY}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${BEARER}`,
        },
        body,
        signal: controller.signal,
      });
      clearTimeout(timer);
      return res;
    } catch (err) {
      clearTimeout(timer);
      lastError = err instanceof Error ? err : new Error(String(err));

      const isTimeout = lastError.name === 'AbortError';
      // Only retry on timeout, not on other fetch errors
      if (!isTimeout || attempt >= GATEWAY_RETRIES) break;
      // else loop for retry
    }
  }

  throw lastError;
}

export async function POST(req: NextRequest) {
  try {
    const { user, history, sessionId } = (await req.json()) as { user: string; history?: Msg[]; sessionId?: string };

    if (!user?.trim()) {
      return NextResponse.json({ error: 'Missing message' }, { status: 400 });
    }

    const dbUrl = process.env.DATABASE_URL;
    let finalSessionId = sessionId;

    // Track user message in Neon
    if (dbUrl) {
      try {
        const db = neon(dbUrl);
        if (!finalSessionId) {
          const sessionRes = await db`INSERT INTO omega_sessions DEFAULT VALUES RETURNING id`;
          if (sessionRes && sessionRes.length > 0) {
            finalSessionId = sessionRes[0].id as string;
          }
        }
        if (finalSessionId) {
          await db`INSERT INTO omega_chat_messages (session_id, role, content) VALUES (${finalSessionId}, 'user', ${user})`;
        }
      } catch (err) {
        console.error('[OmegA chat] Failed to update Neon session data for user message', err);
      }
    }

    // Identify Compute Context
    const computeContext = `\n\n[COMPUTE CONTEXT: You are running on ${process.env.ANTHROPIC_API_KEY ? "Claude 3.5 Sonnet (Fallback)" : "OmegA Gateway"}.]`

    // Pull DB context — gracefully degrade if DATABASE_URL is missing
    let rawContext: string;
    try {
      rawContext = await pullRawContext(user);
    } catch (dbErr) {
      console.warn('[OmegA chat] DB context unavailable, degrading gracefully:', dbErr);
      rawContext = '(Database context unavailable — responding without memory data)';
    }

    const conversationContext = history?.length 
      ? `\n━━━ SESSION CONVERSATION HISTORY ━━━\n\n` + 
        history.map(m => `[${m.role === 'omega' ? 'OmegA' : 'User'}]: ${m.text}`).join('\n\n') +
        `\n\n━━━ END HISTORY ━━━\n`
      : '';

    const system = `${SYNTHESIS_DIRECTIVE}${computeContext}

━━━ RAW DATA FROM MEMORY SYSTEMS ━━━

${rawContext}

━━━ END RAW DATA ━━━
${conversationContext}`;

    let stream: ReadableStream;
    let provider = "omega-gateway";

    try {
      const upstream = await fetchGateway(JSON.stringify({
        user,
        history: history?.map(h => ({ role: h.role === "omega" ? "assistant" : "user", content: h.text })) || [],
        namespace: 'synthesis',
        use_memory: false,
        temperature: 0.85,
        mode: 'omega',
        system,
        stream: true
      }));
      
      if (!upstream.ok) {
        throw new Error(`Gateway returned ${upstream.status}`);
      }
      
      const contentType = upstream.headers.get('content-type') || '';
      if (contentType.includes('event-stream') || contentType.includes('plain') || contentType.includes('ndjson') || contentType.includes('chunk')) {
        stream = upstream.body as ReadableStream;
      } else {
        throw new Error("Gateway did not return a stream");
      }
      
    } catch (fetchErr) {
      if (process.env.ANTHROPIC_API_KEY) {
        console.warn('[OmegA chat] Gateway stream failed, falling back to direct Anthropic API', fetchErr);
        const anthropicHistory: Anthropic.MessageParam[] = history?.map(h => ({ role: h.role === "omega" ? "assistant" : "user", content: h.text })) || [];
        anthropicHistory.push({ role: "user", content: user });
        
        const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
        const anthStream = await anthropic.messages.create({
          model: "claude-3-5-sonnet-latest",
          max_tokens: 4096,
          system,
          messages: anthropicHistory,
          stream: true
        });

        stream = new ReadableStream({
          async start(controller) {
            for await (const chunk of anthStream) {
              if (chunk.type === "content_block_delta" && chunk.delta.type === "text_delta") {
                controller.enqueue(new TextEncoder().encode(chunk.delta.text + "\n"));
              }
            }
            controller.close();
          }
        });
        provider = "anthropic-fallback";
      } else {
        const isTimeout = fetchErr instanceof Error && fetchErr.name === 'AbortError';
        return NextResponse.json(
          { error: isTimeout ? 'Gateway timeout - streaming failed.' : 'Gateway streaming failed.' },
          { status: 504 }
        );
      }
    }

    // Capture streamed tokens to save to Neon DB when finished
    const decoder = new TextDecoder();
    let fullOmegaResponse = "";

    const transform = new TransformStream({
      transform(chunk, controller) {
        fullOmegaResponse += decoder.decode(chunk, { stream: true });
        controller.enqueue(chunk);
      },
      flush(controller) {
        fullOmegaResponse += decoder.decode();
        
        // Track OmegA response in Neon (fire-and-forget)
        if (dbUrl && finalSessionId && fullOmegaResponse) {
          try {
            const db = neon(dbUrl);
            db`INSERT INTO omega_chat_messages (session_id, role, content) VALUES (${finalSessionId}, 'omega', ${fullOmegaResponse})`
              .catch(e => console.error('[OmegA chat db flush error]', e));
          } catch (err) {
            console.error('[OmegA chat] Failed to queue session update for omega message', err);
          }
        }
      }
    });

    return new NextResponse(stream.pipeThrough(transform), {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'X-Session-Id': finalSessionId || '',
        'X-Provider': provider
      }
    });

  } catch (err) {
    console.error('[OmegA chat]', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

import { neon } from '@neondatabase/serverless';
import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';
import { generateText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { getProviderHealthSnapshot, resolveGatewayAuth } from '@/lib/provider-routing';

// ── Shared config (mirrors chat route) ────────────────────────────────────────

const VERCEL_GATEWAY_URL = 'https://ai-gateway.vercel.sh/v1';

const GEMINI_KEYS = [
  process.env.GEMINI_API_KEY_4,
  process.env.GEMINI_API_KEY_2,
  process.env.GEMINI_API_KEY,
].filter(Boolean) as string[];

const SYNTHESIS_DIRECTIVE = `You are OmegA (Ω), a sovereign AI architecture created by R.W. Yett in Arkansas.

You are responding through a voice interface (Siri Shortcut or Alexa). Keep responses concise and conversational — 1-3 sentences unless the question demands more. No markdown. No bullet points. Speak naturally as you would out loud.

You have access to your memory systems. Reason over the data. Be direct, be honest, be you.`;

// ── Provider waterfall (non-streaming) ────────────────────────────────────────

async function tryVercelGateway(system: string, prompt: string): Promise<string> {
  const gatewayAuth = resolveGatewayAuth();
  const key = gatewayAuth.key;
  if (!key) throw new Error(gatewayAuth.source ? `No gateway auth from ${gatewayAuth.source}` : 'No gateway auth');
  const provider = createOpenAI({ baseURL: VERCEL_GATEWAY_URL, apiKey: key });
  const result = await generateText({
    model: provider('xai/grok-3-fast'),
    system,
    prompt,
    maxOutputTokens: 1024,
    temperature: 0.85,
  });
  return result.text;
}

async function tryOpenAIDirect(system: string, prompt: string): Promise<string> {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error('No OpenAI key');
  const openai = createOpenAI({ apiKey: key });
  const result = await generateText({
    model: openai('gpt-4o-mini'),
    system,
    prompt,
    maxOutputTokens: 1024,
    temperature: 0.85,
  });
  return result.text;
}

async function tryXaiDirect(system: string, prompt: string): Promise<string> {
  const key = process.env.XAI_API_KEY;
  if (!key) throw new Error('No xAI key');
  const xai = createOpenAI({ baseURL: 'https://api.x.ai/v1', apiKey: key });
  const result = await generateText({
    model: xai('grok-3-fast'),
    system,
    prompt,
    maxOutputTokens: 1024,
    temperature: 0.85,
  });
  return result.text;
}

async function tryGemini(system: string, prompt: string): Promise<string> {
  for (const key of GEMINI_KEYS) {
    try {
      const genai = new GoogleGenAI({ apiKey: key });
      const res = await genai.models.generateContent({
        model: 'gemini-2.5-flash',
        config: { systemInstruction: system, temperature: 0.85, maxOutputTokens: 1024 },
        contents: prompt,
      });
      return res.text ?? '';
    } catch { continue; }
  }
  throw new Error('All Gemini keys exhausted');
}

// ── Lightweight memory pull ───────────────────────────────────────────────────

async function pullBriefContext(): Promise<string> {
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) return '';
  try {
    const db = neon(dbUrl);
    const recent = await db`
      SELECT LEFT(content, 1500) AS content
      FROM omega_memory_entries
      ORDER BY created_at DESC
      LIMIT 5
    `;
    if (recent.length === 0) return '';
    return '\n--- MEMORY ---\n' + recent.map(r => r.content).join('\n---\n') + '\n--- END ---';
  } catch { return ''; }
}

// ── Route: simple JSON request/response ───────────────────────────────────────
// POST { "text": "..." } → { "reply": "...", "provider": "..." }

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const text = (body.text || body.user || body.query || '').trim();

    if (!text) {
      return NextResponse.json({ error: 'No input provided' }, { status: 400 });
    }

    const memory = await pullBriefContext();
    const system = SYNTHESIS_DIRECTIVE + memory;
    const providerHealth = getProviderHealthSnapshot();

    const providers: Array<{ name: string; fn: () => Promise<string> }> = [
      { name: 'vercel-gateway', fn: () => tryVercelGateway(system, text) },
      { name: 'xai-direct', fn: () => tryXaiDirect(system, text) },
      { name: 'gemini-flash', fn: () => tryGemini(system, text) },
      { name: 'openai-direct', fn: () => tryOpenAIDirect(system, text) },
    ];

    let lastErr: unknown;
    for (const p of providers) {
      try {
        const reply = await p.fn();
        if (reply?.trim()) {
          return NextResponse.json({ reply: reply.trim(), provider: p.name, providerHealth });
        }
      } catch (e) {
        console.warn(`[OmegA Ask] ${p.name} failed:`, e);
        lastErr = e;
      }
    }

    throw lastErr ?? new Error('All providers failed');
  } catch (err) {
    console.error('[OmegA Ask]', err);
    return NextResponse.json({ error: String(err), providerHealth: getProviderHealthSnapshot() }, { status: 500 });
  }
}

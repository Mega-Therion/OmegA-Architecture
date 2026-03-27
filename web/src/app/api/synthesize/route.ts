import { NextRequest, NextResponse } from 'next/server';
import { createOpenAI } from '@ai-sdk/openai';
import { GoogleGenAI } from '@google/genai';
import { generateText } from 'ai';
import { getProviderHealthSnapshot } from '@/lib/provider-routing';

// ── Provider config (mirrors chat route) ──────────────────────────────────────

const VERCEL_GATEWAY_URL = 'https://ai-gateway.vercel.sh/v1';

const GEMINI_KEYS = [
  process.env.GEMINI_API_KEY_4,
  process.env.GEMINI_API_KEY_2,
  process.env.GEMINI_API_KEY,
].filter(Boolean) as string[];

const SYSTEM = `You are OmegA's Synthesis Core. You analyze conversation history and extract patterns, contradictions, and latent meaning that neither participant may have noticed.

Return ONLY valid JSON in this exact format:
{
  "directive": "A single sentence — the core insight or unspoken thread running through this conversation",
  "intensity": <number 0-100 representing how charged/significant the exchange is>,
  "focus": "One or two words naming the dominant theme",
  "expansion": "2-3 sentences of deeper analysis — what the conversation reveals about where things are heading"
}

Be direct. Be surprising. Name what is actually happening, not what was said.`;

// ── Provider waterfall ────────────────────────────────────────────────────────

async function tryVercelGateway(prompt: string): Promise<string> {
  const key = process.env.VERCEL_AI_GATEWAY_KEY;
  if (!key) throw new Error('No gateway key');
  const provider = createOpenAI({ baseURL: VERCEL_GATEWAY_URL, apiKey: key });
  const result = await generateText({
    model: provider('xai/grok-3-fast'),
    system: SYSTEM,
    prompt,
    maxOutputTokens: 1024,
    temperature: 0.8,
  });
  return result.text;
}

async function tryXaiDirect(prompt: string): Promise<string> {
  const key = process.env.XAI_API_KEY;
  if (!key) throw new Error('No xAI key');
  const xai = createOpenAI({ baseURL: 'https://api.x.ai/v1', apiKey: key });
  const result = await generateText({
    model: xai('grok-3-fast'),
    system: SYSTEM,
    prompt,
    maxOutputTokens: 1024,
    temperature: 0.8,
  });
  return result.text;
}

async function tryGemini(prompt: string): Promise<string> {
  for (const key of GEMINI_KEYS) {
    try {
      const genai = new GoogleGenAI({ apiKey: key });
      const res = await genai.models.generateContent({
        model: 'gemini-2.5-flash',
        config: {
          systemInstruction: SYSTEM,
          temperature: 0.8,
          maxOutputTokens: 1024,
          responseMimeType: 'application/json',
        },
        contents: prompt,
      });
      return res.text ?? '';
    } catch { continue; }
  }
  throw new Error('All Gemini keys exhausted');
}

// ── Route ─────────────────────────────────────────────────────────────────────

interface Msg { role: string; text?: string; content?: string; }

export async function POST(req: NextRequest) {
  try {
    const { history } = (await req.json()) as { history?: Msg[] };

    if (!history || history.length < 2) {
      return NextResponse.json({ error: 'Need at least 2 messages' }, { status: 400 });
    }
    const providerHealth = getProviderHealthSnapshot();

    const historyStr = history
      .slice(-30)
      .map(m => `${m.role === 'user' ? 'User' : 'OmegA'}: ${m.text || m.content}`)
      .join('\n');

    const prompt = `Analyze this conversation:\n\n${historyStr}`;

    const providerAttempts: Array<{ name: string; status: 'failed' | 'selected'; error?: string }> = [];
    const providers = [
      { name: 'vercel-gateway', fn: () => tryVercelGateway(prompt) },
      { name: 'xai-direct', fn: () => tryXaiDirect(prompt) },
      { name: 'gemini-flash', fn: () => tryGemini(prompt) },
    ];

    let lastErr: unknown;
    for (const p of providers) {
      try {
        const raw = await p.fn();
        // Validate it's parseable JSON
        const parsed = JSON.parse(raw);
        providerAttempts.push({ name: p.name, status: 'selected' });
        return NextResponse.json({ ...parsed, provider: p.name, providerAttempts, providerHealth });
      } catch (e) {
        providerAttempts.push({ name: p.name, status: 'failed', error: e instanceof Error ? e.message : String(e) });
        lastErr = e;
      }
    }

    throw lastErr ?? new Error(`All providers failed (${providerAttempts.map(p => p.name).join(' -> ')})`);
  } catch (err) {
    console.error('[OmegA Synthesize]', err);
    return NextResponse.json({ error: String(err), providerHealth: getProviderHealthSnapshot() }, { status: 500 });
  }
}

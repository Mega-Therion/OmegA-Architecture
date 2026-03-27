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

const SYSTEM = `You are OmegA's Input Refinement Layer. Your job is to take a user's raw input and rewrite it as a sharper, more precise version of what they meant — without changing their intent. Return ONLY the refined text, nothing else. No quotes, no explanation, no preamble. If the input is already precise, return it unchanged.`;

// ── Provider waterfall ────────────────────────────────────────────────────────

async function tryVercelGateway(text: string): Promise<string> {
  const key = process.env.VERCEL_AI_GATEWAY_KEY;
  if (!key) throw new Error('No gateway key');
  const provider = createOpenAI({ baseURL: VERCEL_GATEWAY_URL, apiKey: key });
  const result = await generateText({
    model: provider('xai/grok-3-fast'),
    system: SYSTEM,
    prompt: text,
    maxOutputTokens: 512,
    temperature: 0.6,
  });
  return result.text;
}

async function tryOpenAIDirect(text: string): Promise<string> {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error('No OpenAI key');
  const openai = createOpenAI({ apiKey: key });
  const result = await generateText({
    model: openai('gpt-4o-mini'),
    system: SYSTEM,
    prompt: text,
    maxOutputTokens: 512,
    temperature: 0.6,
  });
  return result.text;
}

async function tryXaiDirect(text: string): Promise<string> {
  const key = process.env.XAI_API_KEY;
  if (!key) throw new Error('No xAI key');
  const xai = createOpenAI({ baseURL: 'https://api.x.ai/v1', apiKey: key });
  const result = await generateText({
    model: xai('grok-3-fast'),
    system: SYSTEM,
    prompt: text,
    maxOutputTokens: 512,
    temperature: 0.6,
  });
  return result.text;
}

async function tryGemini(text: string): Promise<string> {
  for (const key of GEMINI_KEYS) {
    try {
      const genai = new GoogleGenAI({ apiKey: key });
      const res = await genai.models.generateContent({
        model: 'gemini-2.5-flash',
        config: { systemInstruction: SYSTEM, temperature: 0.6, maxOutputTokens: 512 },
        contents: text,
      });
      return res.text ?? '';
    } catch { continue; }
  }
  throw new Error('All Gemini keys exhausted');
}

// ── Route ─────────────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  try {
    const { text } = (await req.json()) as { text?: string };
    if (!text?.trim()) {
      return NextResponse.json({ error: 'No text' }, { status: 400 });
    }
    const providerHealth = getProviderHealthSnapshot();

    const providerAttempts: Array<{ name: string; status: 'failed' | 'selected'; error?: string }> = [];
    const providers = [
      { name: 'vercel-gateway', fn: () => tryVercelGateway(text) },
      { name: 'openai-direct', fn: () => tryOpenAIDirect(text) },
      { name: 'xai-direct', fn: () => tryXaiDirect(text) },
      { name: 'gemini-flash', fn: () => tryGemini(text) },
    ];

    let lastErr: unknown;
    for (const p of providers) {
      try {
        const refined = await p.fn();
        if (refined?.trim()) {
          providerAttempts.push({ name: p.name, status: 'selected' });
          return NextResponse.json({ refined: refined.trim(), provider: p.name, providerAttempts, providerHealth });
        }
      } catch (e) {
        providerAttempts.push({ name: p.name, status: 'failed', error: e instanceof Error ? e.message : String(e) });
        lastErr = e;
      }
    }

    throw lastErr ?? new Error(`All providers failed (${providerAttempts.map(p => p.name).join(' -> ')})`);
  } catch (err) {
    console.error('[OmegA Refine]', err);
    return NextResponse.json({ error: String(err), providerHealth: getProviderHealthSnapshot() }, { status: 500 });
  }
}

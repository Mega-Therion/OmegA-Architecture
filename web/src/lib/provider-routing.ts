export type ProviderName = 'vercel-gateway' | 'openai-direct' | 'xai-direct' | 'gemini-flash';

export type ProviderAttempt = {
  name: ProviderName;
  status: 'failed' | 'selected';
  error?: string;
};

export type ProviderHealthSnapshot = {
  gateway: {
    configured: boolean;
    available: boolean;
    reason: string | null;
    url: string;
  };
  openai: {
    configured: boolean;
    available: boolean;
    reason: string | null;
  };
  xai: {
    configured: boolean;
    available: boolean;
    reason: string | null;
  };
  gemini: {
    configured: boolean;
    available: boolean;
    reason: string | null;
    keysConfigured: number;
  };
  preferredOrder: ProviderName[];
};

export const DEFAULT_PROVIDER_ORDER: ProviderName[] = [
  'vercel-gateway',
  'xai-direct',
  'gemini-flash',
  'openai-direct',
];

const GEMINI_KEYS = [
  process.env.GEMINI_API_KEY_4,
  process.env.GEMINI_API_KEY_2,
  process.env.GEMINI_API_KEY,
].filter(Boolean) as string[];

export function getProviderHealthSnapshot(): ProviderHealthSnapshot {
  const gatewayConfigured = Boolean(process.env.VERCEL_AI_GATEWAY_KEY);
  const openaiConfigured = Boolean(process.env.OPENAI_API_KEY);
  const xaiConfigured = Boolean(process.env.XAI_API_KEY);
  const geminiConfigured = GEMINI_KEYS.length > 0;

  return {
    gateway: {
      configured: gatewayConfigured,
      available: gatewayConfigured,
      reason: gatewayConfigured ? null : 'missing gateway key',
      url: 'https://ai-gateway.vercel.sh/v1',
    },
    openai: {
      configured: openaiConfigured,
      available: openaiConfigured,
      reason: openaiConfigured ? null : 'missing OpenAI key',
    },
    xai: {
      configured: xaiConfigured,
      available: xaiConfigured,
      reason: xaiConfigured ? null : 'missing xAI key',
    },
    gemini: {
      configured: geminiConfigured,
      available: geminiConfigured,
      reason: geminiConfigured ? null : 'missing Gemini key(s)',
      keysConfigured: GEMINI_KEYS.length,
    },
    preferredOrder: DEFAULT_PROVIDER_ORDER,
  };
}

export function getProviderOrder(): ProviderName[] {
  return DEFAULT_PROVIDER_ORDER;
}

export function serializeProviderHealth(snapshot: ProviderHealthSnapshot): string {
  return JSON.stringify(snapshot);
}

export async function selectStreamingProvider(
  providers: Array<{ name: ProviderName; fn: () => Promise<ReadableStream> }>,
  encoder: TextEncoder,
  decoder: TextDecoder,
): Promise<{
  provider: ProviderName;
  stream: ReadableStream;
  attempts: ProviderAttempt[];
}> {
  let lastErr: unknown;
  const attempts: ProviderAttempt[] = [];

  for (const p of providers) {
    try {
      const providerStream = await p.fn();
      const selected = await promoteNonEmptyStream(providerStream, encoder, decoder);
      if (selected) {
        attempts.push({ name: p.name, status: 'selected' });
        return { provider: p.name, stream: selected, attempts };
      }
      attempts.push({ name: p.name, status: 'failed', error: 'empty response' });
    } catch (e) {
      const error = e instanceof Error ? e.message : String(e);
      attempts.push({ name: p.name, status: 'failed', error });
      lastErr = e;
    }
  }

  throw lastErr ?? new Error(`All providers failed (${attempts.map(p => p.name).join(' -> ')})`);
}

async function promoteNonEmptyStream(
  providerStream: ReadableStream,
  encoder: TextEncoder,
  decoder: TextDecoder,
): Promise<ReadableStream | null> {
  const reader = providerStream.getReader();
  const bufferedChunks: string[] = [];
  let sawMeaningfulChunk = false;

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      if (text) {
        bufferedChunks.push(text);
        if (text.trim()) {
          sawMeaningfulChunk = true;
          break;
        }
      }
    }

    if (!sawMeaningfulChunk) {
      await reader.cancel().catch(() => {});
      return null;
    }

    return new ReadableStream({
      async start(ctrl) {
        try {
          for (const chunk of bufferedChunks) {
            ctrl.enqueue(encoder.encode(chunk));
          }
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const text = decoder.decode(value, { stream: true });
            if (text) ctrl.enqueue(encoder.encode(text));
          }
          ctrl.close();
        } catch (err) {
          ctrl.error(err);
        }
      },
    });
  } catch (err) {
    await reader.cancel().catch(() => {});
    throw err;
  }
}

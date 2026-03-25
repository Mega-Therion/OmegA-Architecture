import { NextRequest, NextResponse } from 'next/server';

// ── Gemini key rotation (same pool as chat route) ─────────────────────────────
const GEMINI_KEYS = [
  process.env.GEMINI_API_KEY_4,
  process.env.GEMINI_API_KEY_2,
  process.env.GEMINI_API_KEY,
].filter(Boolean) as string[];

const TTS_MODEL = 'gemini-2.5-flash-preview-tts';
const TTS_VOICE = 'Charon';

export async function POST(req: NextRequest) {
  try {
    const { text } = (await req.json()) as { text?: string };

    if (!text?.trim()) {
      return NextResponse.json({ error: 'No text provided' }, { status: 400 });
    }

    // Truncate to prevent abuse — 2000 chars max for TTS
    const safeText = text.slice(0, 2000);

    for (const key of GEMINI_KEYS) {
      try {
        const res = await fetch(
          `https://generativelanguage.googleapis.com/v1beta/models/${TTS_MODEL}:generateContent?key=${key}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              contents: [{ parts: [{ text: safeText }] }],
              generationConfig: {
                responseModalities: ['AUDIO'],
                speechConfig: {
                  voiceConfig: {
                    prebuiltVoiceConfig: { voiceName: TTS_VOICE },
                  },
                },
              },
            }),
          }
        );

        if (!res.ok) {
          console.warn(`[OmegA TTS] Key returned ${res.status}, rotating...`);
          continue;
        }

        const data = await res.json();
        const audioPart = data.candidates?.[0]?.content?.parts?.find(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (p: any) => p.inlineData
        );

        if (audioPart?.inlineData?.data) {
          return NextResponse.json({ audio: audioPart.inlineData.data });
        }

        console.warn('[OmegA TTS] No audio data in response, rotating...');
      } catch (e) {
        console.warn('[OmegA TTS] Key failed:', e);
      }
    }

    return NextResponse.json({ error: 'TTS unavailable — all keys exhausted' }, { status: 503 });
  } catch (err) {
    console.error('[OmegA TTS] Route error:', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

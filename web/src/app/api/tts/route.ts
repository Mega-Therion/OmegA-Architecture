import { NextRequest, NextResponse } from 'next/server';

const GEMINI_KEYS = [
  process.env.GEMINI_API_KEY_4,
  process.env.GEMINI_API_KEY_2,
  process.env.GEMINI_API_KEY,
].filter(Boolean) as string[];

const TTS_MODEL = 'gemini-2.5-flash-preview-tts';
const TTS_VOICE = 'Charon';

// Wrap raw LINEAR16 PCM bytes in a WAV container so browsers can decode it
function pcmToWav(pcmBuffer: Buffer, sampleRate = 24000, channels = 1, bitDepth = 16): Buffer {
  const byteRate = sampleRate * channels * (bitDepth / 8);
  const blockAlign = channels * (bitDepth / 8);
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + pcmBuffer.length, 4);
  header.write('WAVE', 8);
  header.write('fmt ', 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);       // PCM
  header.writeUInt16LE(channels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(byteRate, 28);
  header.writeUInt16LE(blockAlign, 32);
  header.writeUInt16LE(bitDepth, 34);
  header.write('data', 36);
  header.writeUInt32LE(pcmBuffer.length, 40);
  return Buffer.concat([header, pcmBuffer]);
}

export async function POST(req: NextRequest) {
  try {
    const { text } = (await req.json()) as { text?: string };
    if (!text?.trim()) return NextResponse.json({ error: 'No text provided' }, { status: 400 });

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
                  voiceConfig: { prebuiltVoiceConfig: { voiceName: TTS_VOICE } },
                },
              },
            }),
          }
        );

        if (!res.ok) { console.warn(`[TTS] Key failed — status ${res.status}`); continue; }

        const data = await res.json();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const part = data.candidates?.[0]?.content?.parts?.find((p: any) => p.inlineData);
        if (!part?.inlineData?.data) continue;

        const pcm = Buffer.from(part.inlineData.data, 'base64');
        const wav = pcmToWav(pcm);
        const wavB64 = wav.toString('base64');

        return NextResponse.json({ audio: wavB64, mimeType: 'audio/wav' });
      } catch (e) {
        console.warn('[TTS] Key failed:', e);
      }
    }

    return NextResponse.json({ error: 'TTS unavailable' }, { status: 503 });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from 'next/server';

/**
 * OmegA STT — Speech-to-Text endpoint
 * Accepts: multipart/form-data with field "audio" (webm/wav/mp3/m4a)
 * Returns: { text: string }
 * Uses OpenAI Whisper API
 */
export async function POST(req: NextRequest) {
  try {
    const key = process.env.OPENAI_API_KEY;
    if (!key) {
      return NextResponse.json({ error: 'STT unavailable — no API key' }, { status: 503 });
    }

    const formData = await req.formData();
    const audioFile = formData.get('audio') as File | null;

    if (!audioFile) {
      return NextResponse.json({ error: 'No audio file provided' }, { status: 400 });
    }

    // Forward to OpenAI Whisper
    const whisperForm = new FormData();
    whisperForm.append('file', audioFile, audioFile.name || 'audio.wav');
    whisperForm.append('model', 'whisper-1');
    whisperForm.append('language', 'en');

    const res = await fetch('https://api.openai.com/v1/audio/transcriptions', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}` },
      body: whisperForm,
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('[OmegA STT] Whisper error:', err);
      return NextResponse.json({ error: 'Transcription failed' }, { status: 502 });
    }

    const data = await res.json();
    return NextResponse.json({ text: data.text ?? '' });
  } catch (err) {
    console.error('[OmegA STT]', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

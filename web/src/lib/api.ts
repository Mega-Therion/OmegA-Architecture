// Chat now routes through /api/chat (server-side) which pulls raw DB context
// before calling the gateway. No static biography — OmegA synthesizes from data.

export interface ChatRequest {
  user: string;
  history?: { role: "user" | "omega"; text: string; timestamp?: string }[];
  sessionId?: string;
}

export interface ChatResponse {
  reply?: string;
  response?: string;
  provider?: string;
  sessionId?: string;
}

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error((body as { error?: string }).error ?? `${res.status}`);
  }

  return res.json() as Promise<ChatResponse>;
}

export async function chatStream(
  req: ChatRequest, 
  onChunk: (text: string) => void,
  onStatus?: (text: string) => void
): Promise<{ sessionId?: string; provider?: string }> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error((body as { error?: string }).error ?? `${res.status}`);
  }

  const sessionId = res.headers.get('X-Session-Id') || undefined;
  const provider = res.headers.get('X-Provider') || undefined;

  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunkText = decoder.decode(value, { stream: true });
    buffer += chunkText;

    // Split by SSE double newline if it looks like status events are active
    while (buffer.includes('\n\n')) {
      const idx = buffer.indexOf('\n\n');
      const line = buffer.slice(0, idx).trim();
      if (line.startsWith('data: {"type":"status"')) {
        try {
          const json = JSON.parse(line.slice(5));
          if (onStatus) onStatus(json.text);
          buffer = buffer.slice(idx + 2);
          continue;
        } catch {
          // fallback if parse fails
        }
      }
      break; // stop if front of buffer isn't a status event
    }

    if (buffer && !buffer.startsWith('data: {"type":"status"')) {
      onChunk(buffer);
      buffer = "";
    }
  }
  
  // Flush remaining buffer
  const final = decoder.decode();
  buffer += final;
  if (buffer) onChunk(buffer);

  return { sessionId, provider };
}

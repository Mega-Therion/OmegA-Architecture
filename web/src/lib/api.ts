// Chat now routes through /api/chat (server-side) which pulls raw DB context
// before calling the gateway. No static biography — OmegA synthesizes from data.

export interface ChatRequest {
  user: string;
  history?: { role: "user" | "omega"; text: string; timestamp?: string }[];
}

export interface ChatResponse {
  reply?: string;
  response?: string;
  provider?: string;
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

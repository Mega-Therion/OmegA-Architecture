const API_BASE = process.env.NEXT_PUBLIC_OMEGA_API_URL ?? 'http://localhost:8787';
const BEARER   = process.env.NEXT_PUBLIC_OMEGA_BEARER_TOKEN ?? '';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${BEARER}`,
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(`${res.status} — ${(body as { detail?: string; message?: string }).detail ?? (body as { message?: string }).message ?? 'Unknown error'}`);
  }
  return res.json() as Promise<T>;
}

// ── Health ────────────────────────────────────────────────────────────────────

export interface GatewayHealth {
  status: string;
  version: string;
  service: string;
}

export async function getGatewayHealth(): Promise<GatewayHealth> {
  return request<GatewayHealth>('/health');
}

// ── Providers ─────────────────────────────────────────────────────────────────

export interface Provider {
  name: string;
  enabled: boolean;
}

export async function getProviders(): Promise<{ providers: Provider[] }> {
  return request<{ providers: Provider[] }>('/api/v1/providers');
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatRequest {
  user: string;
  namespace?: string;
  use_memory?: boolean;
  temperature?: number;
  mode?: string;
}

export interface ChatResponse {
  response: string;
  provider?: string;
  memory_hits?: unknown[];
}

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>('/api/v1/chat', {
    method: 'POST',
    body: JSON.stringify({
      namespace: 'default',
      use_memory: true,
      temperature: 0.4,
      mode: 'local',
      ...req,
    }),
  });
}

// ── Memory ────────────────────────────────────────────────────────────────────

export interface MemoryHit {
  id: string;
  content: string;
  score?: number;
  namespace?: string;
}

export interface MemoryQueryResponse {
  hits: MemoryHit[];
}

export async function queryMemory(
  query: string,
  namespace = 'default',
  limit = 5,
): Promise<MemoryQueryResponse> {
  return request<MemoryQueryResponse>('/api/v1/memory/query', {
    method: 'POST',
    body: JSON.stringify({ query, namespace, limit }),
  });
}

// ── System status (health + providers bundled) ────────────────────────────────

export interface SystemStatus {
  gateway: GatewayHealth;
  providers: Provider[];
}

export async function getSystemStatus(): Promise<SystemStatus> {
  const [gateway, { providers }] = await Promise.all([
    getGatewayHealth(),
    getProviders(),
  ]);
  return { gateway, providers };
}

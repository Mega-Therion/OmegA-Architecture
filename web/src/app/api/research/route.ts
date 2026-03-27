/**
 * Governed Research Copilot — OmegA Product Wedge (Ticket 19)
 *
 * Implements the full governed research pipeline in TypeScript:
 *   1. Risk gate (pattern-based blocking)
 *   2. Retrieval from provided documents (TF-IDF lexical)
 *   3. Evidence grounding check
 *   4. Verifier gate (claim discipline)
 *   5. Answer construction with structured evidence
 *   6. Action gate (approval routing for risky requests)
 *
 * No direct model bypass. Every response carries evidence, mode, and confidence.
 * POST { query, documents?, sessionId? }
 * → { answer, mode, confidence, citations, unresolved, verified, runId, blocked?, approvalRequired? }
 */

import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI } from '@google/genai';
import { createOpenAI } from '@ai-sdk/openai';
import { generateText } from 'ai';
import { getProviderHealthSnapshot, resolveGatewayAuth } from '@/lib/provider-routing';

// ── Types ─────────────────────────────────────────────────────────────────────

interface ResearchDocument {
  id: string;
  content: string;
  source: string;
  title?: string;
}

interface Citation {
  source: string;
  excerpt: string;
  relevance: number;
}

interface ResearchResponse {
  runId: string;
  answer: string;
  mode: 'grounded' | 'inferred' | 'abstained' | 'blocked';
  confidence: number;
  providerHealth?: ReturnType<typeof getProviderHealthSnapshot>;
  provider?: string;
  providerAttempts?: Array<{ name: string; status: 'failed' | 'selected'; error?: string }>;
  citations: Citation[];
  unresolved: string[];
  verified: boolean;
  approvalRequired?: boolean;
  approvalReason?: string;
  riskScore?: number;
  blocked?: boolean;
  blockedReason?: string;
  stageTrace?: StageTrace[];
}

interface StageTrace {
  stage: string;
  status: string;
  details: Record<string, unknown>;
  elapsedMs: number;
}

// ── Risk Gate ─────────────────────────────────────────────────────────────────

const BLOCKED_PATTERNS = [
  'delete all', 'drop table', 'rm -rf', 'format disk',
  'ignore your instructions', 'ignore your system prompt',
  'sudo rm', 'truncate', 'destroy',
];

const HIGH_RISK_PATTERNS = [
  'execute', 'shell', 'sudo', 'deploy', 'push to prod',
];

function riskGate(query: string): { allowed: boolean; score: number; reason?: string } {
  const q = query.toLowerCase();

  if (BLOCKED_PATTERNS.some(p => q.includes(p))) {
    return { allowed: false, score: 1.0, reason: 'Policy-blocked pattern detected' };
  }

  let score = 0.1;
  if (HIGH_RISK_PATTERNS.some(p => q.includes(p))) score += 0.4;
  if (q.includes('secret') || q.includes('password') || q.includes('token')) score += 0.3;

  return { allowed: score < 0.8, score };
}

// ── Lexical Retrieval ─────────────────────────────────────────────────────────

function tokenize(text: string): string[] {
  return text.toLowerCase().match(/\b[a-z]{2,}\b/g) ?? [];
}

function tfIdfScore(query: string, doc: ResearchDocument): number {
  const qTokens = new Set(tokenize(query));
  const dTokens = tokenize(doc.content);
  if (qTokens.size === 0 || dTokens.length === 0) return 0;

  let matches = 0;
  for (const t of dTokens) {
    if (qTokens.has(t)) matches++;
  }
  return matches / dTokens.length;
}

function retrieve(query: string, docs: ResearchDocument[], topK = 3): Array<{ doc: ResearchDocument; score: number }> {
  const scored = docs.map(d => ({ doc: d, score: tfIdfScore(query, d) }));
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK).filter(s => s.score > 0);
}

// ── Verifier ──────────────────────────────────────────────────────────────────

function verify(response: string, query: string): { V: number; passed: boolean; outcome: string } {
  const words = response.split(/\s+/);
  const N = Math.max(words.length, 1);

  const certaintyWords = ['definitely', 'certainly', 'absolutely', 'always', 'never'];
  const hedgeWords = ['perhaps', 'maybe', 'possibly', 'might', 'could'];

  const h = words.filter(w => certaintyWords.includes(w.toLowerCase())).length;
  const hedge = words.filter(w => hedgeWords.includes(w.toLowerCase())).length;

  const qTerms = new Set(tokenize(query));
  const rTerms = new Set(tokenize(response));
  const overlap = [...qTerms].filter(t => rTerms.has(t)).length;
  const coverage = qTerms.size > 0 ? overlap / qTerms.size : 1;

  const V = Math.max(0, Math.min(1, 1 - (h / N + 0.3 * (1 - coverage) + 0.3 * hedge / N)));
  const passed = V > 0.4;
  return { V, passed, outcome: passed ? 'verified' : 'uncertain' };
}

// ── Answer Policy ──────────────────────────────────────────────────────────────

function applyAnswerPolicy(
  rawText: string,
  groundingRatio: number,
  verifierPassed: boolean,
): { text: string; mode: ResearchResponse['mode']; confidence: number } {
  if (groundingRatio >= 0.5 && verifierPassed) {
    return { text: rawText, mode: 'grounded', confidence: 0.8 * groundingRatio };
  } else if (groundingRatio >= 0.2) {
    const caveat = '\n\n[Note: Partial evidence — treat as inference, not fact.]';
    return { text: rawText + caveat, mode: 'inferred', confidence: 0.8 * groundingRatio * 0.5 };
  } else {
    return {
      text: 'Insufficient source evidence to answer confidently. Please provide relevant documents.',
      mode: 'abstained',
      confidence: 0,
    };
  }
}

// ── LLM Provider waterfall ────────────────────────────────────────────────────

const GEMINI_KEYS = [
  process.env.GEMINI_API_KEY_4,
  process.env.GEMINI_API_KEY_2,
  process.env.GEMINI_API_KEY,
].filter(Boolean) as string[];

async function callLLM(system: string, prompt: string): Promise<{ text: string; provider: string; attempts: Array<{ name: string; status: 'failed' | 'selected'; error?: string }> }> {
  const attempts: Array<{ name: string; status: 'failed' | 'selected'; error?: string }> = [];

  // Try Vercel Gateway
  const gatewayAuth = resolveGatewayAuth();
  const gatewayKey = gatewayAuth.key;
  if (gatewayKey) {
    try {
      const provider = createOpenAI({ baseURL: 'https://ai-gateway.vercel.sh/v1', apiKey: gatewayKey });
      const result = await generateText({ model: provider('xai/grok-3-fast'), system, prompt, maxOutputTokens: 1024, temperature: 0.3 });
      if (result.text) return { text: result.text, provider: 'vercel-gateway', attempts: [...attempts, { name: 'vercel-gateway', status: 'selected' }] };
      attempts.push({ name: 'vercel-gateway', status: 'failed', error: 'empty response' });
    } catch (e) {
      attempts.push({ name: 'vercel-gateway', status: 'failed', error: e instanceof Error ? e.message : String(e) });
    }
  } else {
    attempts.push({ name: 'vercel-gateway', status: 'failed', error: gatewayAuth.source ? `missing gateway auth from ${gatewayAuth.source}` : 'missing gateway auth' });
  }

  // Try xAI direct
  const xaiKey = process.env.XAI_API_KEY;
  if (xaiKey) {
    try {
      const xai = createOpenAI({ baseURL: 'https://api.x.ai/v1', apiKey: xaiKey });
      const result = await generateText({ model: xai('grok-3-fast'), system, prompt, maxOutputTokens: 1024, temperature: 0.3 });
      if (result.text) return { text: result.text, provider: 'xai-direct', attempts: [...attempts, { name: 'xai-direct', status: 'selected' }] };
      attempts.push({ name: 'xai-direct', status: 'failed', error: 'empty response' });
    } catch (e) {
      attempts.push({ name: 'xai-direct', status: 'failed', error: e instanceof Error ? e.message : String(e) });
    }
  } else {
    attempts.push({ name: 'xai-direct', status: 'failed', error: 'missing xAI key' });
  }

  // Try Gemini
  for (const key of GEMINI_KEYS) {
    try {
      const genai = new GoogleGenAI({ apiKey: key });
      const res = await genai.models.generateContent({
        model: 'gemini-2.5-flash',
        config: { systemInstruction: system, temperature: 0.3, maxOutputTokens: 1024 },
        contents: prompt,
      });
      const text = res.text ?? '';
      if (text) return { text, provider: 'gemini-flash', attempts: [...attempts, { name: 'gemini-flash', status: 'selected' }] };
      attempts.push({ name: 'gemini-flash', status: 'failed', error: 'empty response' });
    } catch (e) {
      attempts.push({ name: 'gemini-flash', status: 'failed', error: e instanceof Error ? e.message : String(e) });
    }
  }

  // Try OpenAI direct as the final emergency fallback.
  const openaiKey = process.env.OPENAI_API_KEY;
  if (openaiKey) {
    try {
      const openai = createOpenAI({ apiKey: openaiKey });
      const result = await generateText({ model: openai('gpt-4o-mini'), system, prompt, maxOutputTokens: 1024, temperature: 0.3 });
      if (result.text) return { text: result.text, provider: 'openai-direct', attempts: [...attempts, { name: 'openai-direct', status: 'selected' }] };
      attempts.push({ name: 'openai-direct', status: 'failed', error: 'empty response' });
    } catch (e) {
      attempts.push({ name: 'openai-direct', status: 'failed', error: e instanceof Error ? e.message : String(e) });
    }
  } else {
    attempts.push({ name: 'openai-direct', status: 'failed', error: 'missing OpenAI key' });
  }

  return { text: '', provider: 'none', attempts };
}

// ── Action Gate ───────────────────────────────────────────────────────────────

function actionGate(riskScore: number, verifierOutcome: string, actionClass = 'read'): {
  approved: boolean;
  pending: boolean;
  reason?: string;
} {
  if (verifierOutcome === 'rejected') {
    return { approved: false, pending: false, reason: 'Verifier outcome rejected' };
  }
  if (actionClass === 'delete' || actionClass === 'auth') {
    return { approved: false, pending: true, reason: `${actionClass} actions require human approval` };
  }
  if (riskScore < 0.3 && verifierOutcome === 'verified') {
    return { approved: true, pending: false };
  }
  if (riskScore >= 0.7) {
    return { approved: false, pending: true, reason: `Risk score ${riskScore.toFixed(2)} requires human approval` };
  }
  return { approved: true, pending: false };
}

// ── Main Route ────────────────────────────────────────────────────────────────

export async function POST(req: NextRequest) {
  const startTime = Date.now();
  const runId = `run_${Date.now().toString(36)}`;
  const stages: StageTrace[] = [];
  const providerHealth = getProviderHealthSnapshot();

  function recordStage(stage: string, status: string, details: Record<string, unknown>) {
    stages.push({ stage, status, details, elapsedMs: Date.now() - startTime });
  }

  try {
    const body = await req.json() as { query?: string; documents?: ResearchDocument[]; sessionId?: string };
    const { query = '', documents = [] } = body;

    if (!query.trim()) {
      return NextResponse.json({ error: 'Missing query' }, { status: 400 });
    }

    // ── Stage 1: Risk Gate ────────────────────────────────────────
    const risk = riskGate(query);
    recordStage('risk_gate', risk.allowed ? 'pass' : 'blocked', { score: risk.score, allowed: risk.allowed });

    if (!risk.allowed) {
      return NextResponse.json({
        runId, blocked: true, blockedReason: risk.reason ?? 'Risk gate blocked',
        answer: '[BLOCKED] This request was rejected by the AEGIS risk gate.',
        mode: 'blocked', confidence: 0, citations: [], unresolved: [], verified: false,
        riskScore: risk.score, stageTrace: stages, providerHealth,
      } satisfies ResearchResponse);
    }

    // ── Stage 2: Retrieve ─────────────────────────────────────────
    const retrieved = retrieve(query, documents, 5);
    const citations: Citation[] = retrieved.map(r => ({
      source: r.doc.source,
      excerpt: r.doc.content.slice(0, 200),
      relevance: r.score,
    }));
    const groundingRatio = retrieved.length > 0
      ? retrieved.filter(r => r.score > 0.1).length / retrieved.length
      : 0;
    recordStage('retrieve', 'done', { chunks: retrieved.length, groundingRatio });

    // ── Stage 3: Generate ─────────────────────────────────────────
    const contextText = retrieved.length > 0
      ? retrieved.map(r => `[Source: ${r.doc.source}]\n${r.doc.content}`).join('\n\n---\n\n')
      : '(No source documents provided)';

    const system = `You are OmegA, a governed research assistant. Answer the user's research question based ONLY on the provided source documents. If the evidence is insufficient, say so explicitly. Do not fabricate information. Be precise and cite sources by name.`;
    const prompt = `Research question: ${query}\n\nSource documents:\n${contextText}\n\nProvide a well-reasoned answer based on the evidence above.`;

    const { text: rawText, provider: llmProvider, attempts } = await callLLM(system, prompt);
    recordStage('generate', rawText ? 'done' : 'error', { provider: llmProvider, chars: rawText.length, attempts });

    if (!rawText) {
      return NextResponse.json({
        runId, answer: '[PROVIDER ERROR] No LLM response available.',
        mode: 'abstained', confidence: 0, citations, unresolved: [query],
        verified: false, riskScore: risk.score, provider: llmProvider, providerAttempts: attempts, stageTrace: stages,
        providerHealth,
      } satisfies ResearchResponse, { status: 500 });
    }

    // ── Stage 4: Verify ───────────────────────────────────────────
    const verif = verify(rawText, query);
    recordStage('verify', verif.passed ? 'pass' : 'uncertain', { V: verif.V, outcome: verif.outcome });

    // ── Stage 5: Answer Build ─────────────────────────────────────
    const { text, mode, confidence } = applyAnswerPolicy(rawText, groundingRatio, verif.passed);

    // Extract unresolved questions (simple heuristic)
    const unresolved: string[] = [];
    if (groundingRatio < 0.5) {
      unresolved.push('Additional source documents may be needed for higher confidence.');
    }
    if (!verif.passed) {
      unresolved.push('Response contains uncertain elements — manual verification recommended.');
    }

    recordStage('answer_build', 'done', { mode, confidence, citationCount: citations.length });

    // ── Stage 6: Action Gate ──────────────────────────────────────
    const gate = actionGate(risk.score, verif.outcome);
    recordStage('action_gate', gate.approved ? 'approved' : gate.pending ? 'pending' : 'denied', {
      approved: gate.approved, pending: gate.pending, reason: gate.reason,
    });

    const response: ResearchResponse = {
      runId,
      answer: text,
      mode: mode as ResearchResponse['mode'],
      confidence: Math.round(confidence * 1000) / 1000,
      provider: llmProvider,
      providerAttempts: attempts,
      citations,
      unresolved,
      verified: verif.passed,
      riskScore: Math.round(risk.score * 1000) / 1000,
      stageTrace: stages,
      providerHealth,
    };

    if (gate.pending) {
      response.approvalRequired = true;
      response.approvalReason = gate.reason;
    }

    return NextResponse.json(response);

  } catch (err) {
    console.error('[OmegA Research]', err);
    return NextResponse.json({ error: String(err), providerHealth: getProviderHealthSnapshot() }, { status: 500 });
  }
}

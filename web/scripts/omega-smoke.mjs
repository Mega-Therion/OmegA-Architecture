#!/usr/bin/env node

const args = new Map();
for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i];
  const value = process.argv[i + 1];
  if (key?.startsWith('--')) args.set(key.slice(2), value);
}

const baseUrl = (args.get('base') || process.env.OMEGA_BASE_URL || 'http://localhost:3000').replace(/\/$/, '');
const prompt = args.get('prompt') || 'Explain your operating style in fresh wording. Do not repeat the wording of this prompt.';
const authUser = args.get('auth-user') || process.env.OMEGA_UI_USER || 'omega';
const authPass = args.get('auth-pass') || process.env.OMEGA_UI_PASSWORD || '';

function normalize(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().split(/\s+/).filter(Boolean);
}

function overlapScore(a, b) {
  const aw = normalize(a);
  const bw = normalize(b);
  if (!aw.length || !bw.length) return 0;
  const set = new Set(bw);
  let matches = 0;
  for (const w of aw) if (set.has(w)) matches++;
  return matches / aw.length;
}

const headers = { 'Content-Type': 'application/json' };
if (authPass) {
  headers.Authorization = `Basic ${Buffer.from(`${authUser}:${authPass}`).toString('base64')}`;
}

const chatRes = await fetch(`${baseUrl}/api/chat`, {
  method: 'POST',
  headers,
  body: JSON.stringify({ user: prompt, voiceMode: false }),
});

const sessionId = chatRes.headers.get('x-session-id');
const provider = chatRes.headers.get('x-provider');
const memoryBackend = chatRes.headers.get('x-memory-backend');
const rawReply = await chatRes.text();
const reply = rawReply.replace(/data: \{"type":"status","text":"[^"]*"\}\n\n/g, '').trim();

let sessionMessages = [];
if (sessionId) {
  const sessionRes = await fetch(`${baseUrl}/api/sessions/${sessionId}`, { headers });
  if (sessionRes.ok) sessionMessages = await sessionRes.json();
}

const userMessage = sessionMessages.find((m) => m.role === 'user')?.content ?? '';
const omegaMessage = sessionMessages.find((m) => m.role === 'omega')?.content ?? '';

const report = {
  baseUrl,
  sessionId,
  provider,
  memoryBackend,
  replyLength: reply.length,
  promptOverlap: Number(overlapScore(reply, prompt).toFixed(3)),
  dbRoundTrip: sessionMessages.length >= 2,
  sessionMessageCount: sessionMessages.length,
  storedUserLength: userMessage.length,
  storedOmegaLength: omegaMessage.length,
  replyPreview: reply.slice(0, 240),
};

console.log(JSON.stringify(report, null, 2));

if (!sessionId) process.exitCode = 1;
if (!memoryBackend || memoryBackend === 'none') process.exitCode = 1;
if (!report.dbRoundTrip) process.exitCode = 1;
if (report.promptOverlap > 0.85) process.exitCode = 1;

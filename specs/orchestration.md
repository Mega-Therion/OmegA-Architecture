# Orchestration Subsystem
**Version:** 1.0.0
**Last Updated:** 2026-03-13

The Orchestration subsystem routes requests to the right agent, coordinates multi-agent tasks, manages the provider failover chain, and runs the Sovereign Loop.

---

## What It Is

The layer between "a request came in" and "the right thing happened." It decides:
- Which agent (Claude, Gemini, Codex, Grok) handles which task
- Which LLM provider handles the underlying inference
- Whether a request needs consensus before proceeding
- How to decompose complex tasks into parallel sub-tasks
- When to self-heal if a component fails

---

## Primary Components

### omega_ask.py / router.py (NEXUS Core)
**Location:** `~/NEXUS/core/omega_ask.py`, `~/NEXUS/core/router.py`

`omega_ask.py` routes incoming requests through the Gateway (:8787) → memory retrieval → model routing → response. Falls back to Codex CLI or Claude CLI if Gateway is down.

`router.py` auto-routes based on system load:
- Light/medium tasks on normal load → Local (Ollama)
- Heavy tasks → Cloud (Claude Opus)
- Any task on high system load → Cloud (Gemini Flash)

### Brain Orchestrator (Node.js)
**Location:** `services/packages/brain/src/services/orchestrator.js`

Strategies:
- **Pipeline:** Linear flow (Scout → Strategist → Architect → Builder)
- **Debate:** Multiple agents discuss until agreement (mediated by Gemini)
- **Consensus:** Agents vote via DCBFT kernel
- **Specialist:** Automatic routing to most capable agent for detected intent

### 7-Specialist Subagent Orchestrator
**Location:** `scripts/omega-agents/orchestrator.py`

Phases:
- Phase 1 (serial): **Arius** — Architect (design; fatal on failure)
- Phase 2 (parallel): **Nexus** (backend) + **Iris** (frontend) + **Datum** (data)
- Phase 3 (parallel): **Atlas** (devops) + **Aegis** (security) + **Verity** (QA)

SQLite message bus at `agents/state.db` (WAL mode). Shared workspace at `agents/workspace/`.

### Provider Failover Chain (Gateway)
**Location:** `rust/omega-rust/crates/omega-provider/`

On 429/402/5xx errors:
```
perplexity → deepseek → gemini → anthropic → local (Ollama)
```

All 6 provider clients have 60s timeout. Circuit breakers prevent credit hemorrhage on sustained failures.

### Sovereign Loop
**Location:** `server/_core/sovereign_loop.js` (design) / Brain startup

Cycle interval: 30 seconds
```
OBSERVE → THINK → ACT → VERIFY → REMEMBER
```
- OBSERVE: Ping all service health endpoints
- THINK: Analyze health state; identify anomalies
- ACT: Attempt self-healing; escalate to RY if needed
- VERIFY: Confirm actions succeeded
- REMEMBER: Write cycle outcome to memory

---

## ORYAN Task Queue
**Location:** `~/NEXUS/OmegA/OmegA-SI/tools/ORYAN/`

SQLite-backed task queue for batch agent operations. Coordinates Claude, Gemini, Codex via CLI wrappers. Outputs stored in `omega_runs/<timestamp>/`.

Commands: `./oryan task create --agent claude --prompt "..."` → `./oryan run latest`

---

## Current Implementation Status

| Component | Status |
|-----------|--------|
| omega_ask.py routing | PRODUCTION |
| Brain orchestrator (specialist routing) | PRODUCTION |
| Provider failover chain (Rust) | PRODUCTION — 34/34 tests |
| Council synthesis (omega mode) | PRODUCTION — Week 3 complete |
| 7-specialist orchestrator | PRODUCTION |
| Sovereign Loop | DESIGNED — partial implementation in Brain |
| Hybrid routing (local/cloud by load) | PRODUCTION via router.py |
| ORYAN task queue | PRODUCTION |

---

## Failure Modes

| Failure | Tag | Symptom |
|---------|-----|---------|
| All providers fail failover chain | RUNTIME_ENV | No LLM response available |
| Agent worker crash | ORCHESTRATION | Task lost; Brain should restart worker |
| Sovereign Loop cycle fault | ORCHESTRATION | Error caught; emergency heal attempted |
| Message bus corruption (7-agent) | RUNTIME_ENV | Phase 2/3 agents can't receive tasks |
| Brain fails to delegate to Bridge | ORCHESTRATION | High-stakes action bypasses consensus |

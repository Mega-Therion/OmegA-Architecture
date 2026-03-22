# OxySpine Trinity — Service Architecture Specification
**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-13
**Operator:** RY (Mega)

OxySpine Trinity is the unified spinal cord of OmegA — the interconnected services that make the system coherent across surfaces. The name references the oxygen-carrying function of a spinal cord: it keeps the whole organism alive and coordinated.

---

## 1. The Three Spinal Services

```
User Input (any adapter)
        ↓
  ADAPTERS (Telegram, Alexa, CLI, REST, HUD)
        ↓  [Resonance Headers]
  GATEWAY :8787  ← sovereign ingress, auth, policy enforcement
        ↓
   ┌────┴─────────────────────────┐
   │ Low stakes                High stakes / governance
   ↓                               ↓
BRAIN :8080              BRIDGE :8000
Orchestration            Peace Pipe Protocol
Memory operations        DCBFT Consensus
Tool routing             Artifact generation
LLM dispatch             Chief Ruling enforcement
   ↓                               ↓
   └────────────┬─────────────────┘
                ↓
         PHYLACTERY (L6 Memory)
         Identity Kernel
                ↓
         MEMORY VAULT (L1–L5)
```

---

## 2. Service Definitions

### HUD — Internal Operator Surface
**Port:** 3000
**Health:** `http://localhost:3000/api/health`
**Stack:** Next.js 15, React 19, TypeScript, TailwindCSS 4, tRPC client
**Location:** `services/packages/hud/`

**Purpose:** Internal command console and system observation surface for RY. Not a public product.
**What it does:** Displays agent roster, council chamber, memory governance, policy view, forensic trace viewer, system health dashboard.
**Authority:** Read/write controls for the operator. Never the source of truth — it displays what Brain and Bridge know.
**Inputs:** HTTP from Brain (:8080) via tRPC. WebSocket for real-time updates.
**Outputs:** Operator commands dispatched to Brain.
**Failure modes:**
- HUD down: system continues operating; operator loses visibility but functionality is unaffected
- HUD/Brain sync lag: expected during heavy thought cycles; the HUD may show stale state

**Access:** Internal only (Tailscale/VPN). Never expose to public internet.

---

### Brain — Orchestration and Memory
**Port:** 8080
**Health:** `http://localhost:8080/health`
**Stack:** Node.js, Express, tRPC server, Drizzle ORM, MySQL2
**Location:** `services/packages/brain/`

**Purpose:** Primary API, memory orchestration, agent routing, and tool execution. Contains the Brain Stem role — the central orchestrator that parses Resonance headers, coordinates retrieval and reasoning, enforces authority and consent, and synthesizes responses.
**What it does:**
- Routes requests to appropriate agents (specialist routing)
- Manages multi-tier memory (working, session, semantic, episodic)
- Executes tools via the Tool Registry
- Runs the Sovereign Loop (health watchdog: 30s cycles, observe→think→act→verify→remember)
- Manages agent workers (Claude, Gemini, Codex, Grok workers)
- Connects to Supabase for persistent memory
- Implements circuit breakers and exponential backoff on external dependencies
**Inputs:** HTTP from HUD (tRPC), Gateway (:8787), adapters
**Outputs:** Synthesized responses, memory writes, tool results, Bridge delegation for high-stakes actions
**Failure modes:**
- Brain down: CRITICAL — no orchestration, no responses. Gateway falls back to direct LLM mode.
- Memory unavailable: Fall back to local SQLite cache; log degradation; alert via Telegram
- Agent worker crash: Brain restarts workers automatically; logs to `~/NEXUS/intelligence/log.json`

---

### Bridge — Governance and Consensus
**Port:** 8000
**Health:** `http://localhost:8000/health`
**Stack:** Python FastAPI, DCBFT consensus, Resonance Protocol
**Location:** `services/packages/bridge/`

**Purpose:** Governance gateway. Implements the Peace Pipe Protocol state machine, DCBFT consensus engine, turn-taking locks, and artifact generation. Routes high-stakes decisions.
**What it does:**
- Enforces Peace Pipe Protocol (open/pipe_granted/submission/synthesis/ruling/close)
- Runs DCBFT voting for multi-agent decisions (N ≥ 3f+1, 2/3 quorum)
- Generates council artifacts (transcript, docket, resolution)
- Prevents unauthorized identity or canon changes from reaching the Phylactery
- Implements the AsyncOrchestrator for parallel agent task dispatch
**Inputs:** High-stakes requests delegated from Brain; direct operator governance commands
**Outputs:** DCBFT consensus outcomes, Peace Pipe artifacts, approved or rejected actions
**Failure modes:**
- Bridge down: Non-CRITICAL for low-stakes operations; CRITICAL for any operation requiring consensus. Brain falls back to logging the action as `CONSENSUS_BYPASSED`.
- Consensus timeout: Treated as ABORT unless emergency override applies (see PEACE_PIPE_PROTOCOL.md §6)

---

### Gateway — Sovereign Ingress
**Port:** 8787
**Health:** `http://localhost:8787/health`
**Stack:** Rust (Axum) — `/home/mega/OmegA-Sovereign/rust/omega-rust/`
**Location:** `rust/omega-rust/crates/omega-gateway/`

**Purpose:** The sovereign LLM proxy and primary ingress point. All external LLM calls pass through here. Enforces auth, policy (LAW.json), Resonance Protocol parsing, provider failover, and local memory.
**What it does:**
- Authenticates all requests (Bearer token: `OMEGA_API_BEARER_TOKEN`)
- Enforces LAW.json forbidden actions and command blocklist
- Routes to LLM providers with automatic failover: perplexity → deepseek → gemini → anthropic → local
- Implements `omega` mode (Council synthesis: parallel Anthropic+Gemini fan-out + synthesis)
- Manages local SQLite memory (`omega-memory` crate, fastembed-rs for semantic search)
- Runs background Dream State (autonomous reflection, Neuro-Credit rewards)
- Runs Proactive Agency (scans memory for high-importance tasks, initiates without user input)
**Performance:** 5.4MB binary, 31ms cold start, 0.6ms health p50, 365–755 req/s
**Inputs:** All inbound requests from adapters and Brain
**Outputs:** LLM responses, memory operations, policy enforcement decisions
**Failure modes:**
- Gateway down: CRITICAL — all LLM calls fail. Brain must queue or fail gracefully.
- Provider failure: Automatic failover chain executes; logs which provider answered
- Auth token missing/empty: Permissive mode (intentional for development). Non-empty token is enforced.
- Missing `Authorization` header → 401. Present but wrong token → 403.

**Not yet systemd-persistent.** Will not survive reboot without:
```bash
sudo cp ~/OmegA-Sovereign/rust/omega-rust/omega-gateway.service.rust-ready \
  /etc/systemd/system/omega-gateway.service
sudo systemctl daemon-reload && sudo systemctl enable --now omega-gateway
```

---

## 3. Data Flow

**Normal request (low stakes):**
```
Adapter → Gateway (auth + policy) → Brain (orchestrate + memory) → LLM Provider → Brain (synthesize) → Adapter
```

**High stakes / governance request:**
```
Adapter → Gateway → Brain → Bridge (Peace Pipe) → DCBFT vote → Chief Ruling → Phylactery update → Brain → Adapter
```

**Memory write:**
```
Brain → Provenance check → Probation queue → (promotion trigger) → L3-L5 Supabase + SQLite
```

**Canon update:**
```
Peace Pipe Council → Chief Ruling → Bridge enforces → Phylactery (L6) version bump
```

---

## 4. Inter-Service Contract Boundaries

Services must communicate through documented contracts only:

| Boundary | Protocol | Contract |
|----------|---------- |----------|
| Gateway ↔ Brain | REST, Bearer token | `docs/API_CONTRACT.md` |
| Brain ↔ Bridge | `bridge-client.js` | Bridge FastAPI schema |
| Brain ↔ HUD | tRPC | `packages/brain/src/routers/` |
| Gateway ↔ Memory | Rust traits | `omega-memory` crate interface |
| Bridge ↔ Consensus | Python async | `consensus_engine.py` AsyncOrchestrator |

No service may reach into another service's database directly without going through the owning service's API.

---

## 5. Health Check Endpoints

| Service | URL | Expected Response |
|---------|-----|-------------------|
| HUD | `http://localhost:3000/api/health` | `{"status": "ok"}` |
| Brain | `http://localhost:8080/health` | `{"status": "ok"}` |
| Bridge | `http://localhost:8000/health` | `{"status": "ok"}` |
| Gateway | `http://localhost:8787/health` | `{"status": "ok"}` |

The Sovereign Loop (Brain) pings all health endpoints every 30 seconds. Missed heartbeat for >30s triggers reboot attempt.

`npm run omega:doctor` runs a comprehensive check across all services.

---

## 6. Service Restart and Recovery Rules

1. **Gateway:** Restart via `cargo run --bin omega-gateway` or (once installed) `systemctl restart omega-gateway`. State is preserved in SQLite.
2. **Brain:** Restart via `npm run dev` or the brain-specific startup command. Agent workers restart automatically.
3. **Bridge:** Restart via `uvicorn api:app --host 0.0.0.0 --port 8000`. Consensus state in Bridge DB persists.
4. **HUD:** Restart via Next.js dev/build. Stateless — no recovery needed.

**Recovery order after full system restart:** Gateway → Bridge → Brain → HUD

---

## 7. Adapters (Non-Spinal Services)

These are integration edges, not spinal services. They call Brain/Bridge through explicit consent scopes:

| Adapter | Port | Purpose |
|---------|------|---------|
| Telegram (omega-workflows) | 9090 | Webhook + income engine |
| Revenue Router | 9091 | Multi-platform income orchestration |
| Alexa | n/a | Alexa Skill adapter |
| n8n | configured | Workflow automation |
| CLI (ORYAN/omega) | n/a | Interactive multi-agent chat |

---

## Known Conflicts

**Conflict 1:** OMEGA_SOVEREIGN_DNA.md (Feb 2026 state) shows Gateway as Python FastAPI. Current reality: Gateway is Rust (Axum), Python is fully replaced. This document reflects current production state.

---

## Changelog

- 1.0.0 (2026-03-13): Initial canonical synthesis from OMEGA_FULL_SYSTEM_SPEC.md, OMEGA_VISION.md, OMEGA_SOVEREIGN_DNA.md, CLAUDE.md. Prior stub was a placeholder.

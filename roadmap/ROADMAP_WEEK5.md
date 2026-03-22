# ROADMAP — Week 5 (Production Hardening + Multi-Node)

**Theme:** production reliability, observability, and running multiple gateway instances safely.

## 1) Structured Observability (OpenTelemetry)
**What:** add end-to-end tracing spans for provider calls, memory operations, and council synthesis; export via OTLP.  
**Why:** makes every request diagnosable (latency, provider used, failure mode, token usage).  
**DoD:**
- Spans for: `/api/v1/chat`, router failover steps, each provider call, memory `write/read/search/delete`, council member calls + synthesis.
- OTLP exporter behind env (`OMEGA_OTEL_EXPORTER_OTLP_ENDPOINT`, `OMEGA_OTEL_SERVICE_NAME`).
- Trace IDs logged in HTTP responses (header) and server logs.
**Effort:** M  
**Deps:** none

## 2) Gateway Rate Limiting
**What:** per-IP (or per-bearer token) rate limit middleware for sensitive endpoints.  
**Why:** prevents runaway clients and protects upstream provider budgets.  
**DoD:**
- Middleware on `/api/v1/chat` and `/api/v1/chat/stream`.
- Config via env (e.g. `OMEGA_RATE_LIMIT_RPS`, `OMEGA_RATE_LIMIT_BURST`).
- Clear 429 response shape + logging.
**Effort:** S–M  
**Deps:** tower middleware choice (`governor` or equivalent)

## 3) Prompt Injection Detection (First-pass)
**What:** lightweight detection of common prompt injection patterns before routing to any LLM.  
**Why:** reduces obvious jailbreaks and “ignore previous instructions” attacks.  
**DoD:**
- Regex-based rule set with logging.
- Config: warn-only vs reject (`OMEGA_INJECTION_MODE=warn|reject`).
- Unit tests for at least 10 patterns.
**Effort:** S  
**Deps:** none

## 4) Multi-node Memory Sync (pgvector path)
**What:** standardize on Postgres/pgvector memory backend for multi-node gateway deployments.  
**Why:** SQLite memory is per-instance; multi-node needs shared state.  
**DoD:**
- Document Supabase schema and required indexes.
- Document connection strings (direct vs pooler) + recommended pool sizes.
- Gateway supports selecting backend via `OMEGA_DB_URL=postgresql://...`.
**Effort:** M  
**Deps:** Supabase credentials + pgvector extension enabled

## 5) Health Deep-check Improvements
**What:** improve `/health/deep` to validate external dependencies.  
**Why:** catches broken provider keys, DB connectivity, and degraded routing early.  
**DoD:**
- Checks memory store connectivity (and entry count).
- Checks configured providers via fast “ping” request (or HEAD) with timeouts.
- Includes last decay run timestamp (SQLite) where available.
**Effort:** M  
**Deps:** provider “ping” strategy agreed

## 6) Binary Distribution (Cross-compile)
**What:** build + publish binaries for common deployment targets, including ARM.  
**Why:** faster installs, easier server deployment.  
**DoD:**
- GitHub Actions workflow building `omega-gateway` for `x86_64-unknown-linux-musl` and `aarch64-unknown-linux-musl`.
- Artifacts attached to releases (or stored as workflow artifacts).
**Effort:** M  
**Deps:** CI runner toolchain setup

## 7) Omega Mode Streaming (SSE for synthesis)
**What:** stream council synthesis output tokens over SSE.  
**Why:** better UX and less perceived latency.  
**DoD:**
- `/api/v1/chat/stream` supports omega mode streaming for synthesis output.
- Backpressure-safe; timeouts and cancellation handled.
**Effort:** M–L  
**Deps:** provider streaming interface consistency


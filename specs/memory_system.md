# Memory System Subsystem
**Version:** 1.0.0
**Last Updated:** 2026-03-13

The Memory System provides OmegA with persistent, provenance-tracked knowledge across sessions. Canonical rules for the memory system are defined in `omega/MEMORY_CONSTITUTION.md`.

---

## What It Is

A multi-tier storage and retrieval system that spans:
- In-process RAM (L1 working memory)
- Session-scoped SQLite/Brain DB (L2 session memory)
- Long-term SQLite via Rust `omega-memory` crate (L3/L4 local)
- Supabase PostgreSQL + pgvector (L4/L5 cloud)
- Version-controlled Phylactery files (L6 identity kernel)

---

## Why It Exists

Stateless LLMs forget everything between requests. OmegA's value proposition is persistent longitudinal memory — the ability to remember past conversations, decisions, project history, and operator preferences across sessions, provider swaps, and system restarts.

---

## Primary Components

### omega-memory Crate (Rust)
**Location:** `rust/omega-rust/crates/omega-memory/`
**Database:** SQLite via sqlx
**Features:**
- `SqliteMemoryStore` — write/read/search/delete operations
- fastembed-rs embeddings (all-MiniLM-L6-v2) stored in SQLite/PG BLOBs
- Semantic LIKE search (Week 3 production); fastembed semantic search is Week 4 work
- Memory CRUD routes exposed via Gateway: `GET /memory`, `POST /memory/upsert`, `DELETE /memory/:id`
- Importance decay background task (hourly tokio task — Week 4 implementation)

### Brain Memory Layer (Node.js)
**Location:** `services/packages/brain/src/core/memory-layer.js`
**Features:**
- Working memory (L1) — in-process
- Session memory (L2) — Brain DB
- Hybrid RAG: local fastembed + Mem0 cloud integration for deep cross-session retrieval

### Supabase (Cloud)
**Project:** `tssfdlodjgtedsssfpfc` (OmegA-Sovereign — omega_memory, omega_events)
**Project:** `sgvitxezqrjgjmduoool` (Primary — chat_messages, files)
- pgvector extension for semantic search (Week 4: `PgMemoryStore` implementation)
- `omega_memory` table, `omega_events` table

---

## Retrieval Logic

1. L1 (current context) — always available, no retrieval needed
2. L6 (Phylactery) — identity anchors, injected at context start
3. L2 (session) — last N messages and session facts
4. L4 (semantic) — vector similarity search against query embedding
5. L3 (episodic) — temporal search for relevant past events
6. L5 (relational) — SQL/graph lookup for structured facts

Retrieval timeout: if semantic search exceeds 2s, fall back to keyword search and log `RETRIEVAL` failure.

---

## Write Path

```
Write request → provenance check (source, timestamp, confidence required)
             → probation queue (if not explicitly promoted)
             → [promotion trigger] → L3/L4/L5 storage
             → contradiction detection → conflict flag if match found
```

---

## Current Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| SQLite write/read/delete | PRODUCTION | Week 2 complete; 34/34 tests pass |
| Memory CRUD routes via Gateway | PRODUCTION | GET/DELETE by ID live |
| Session memory (Brain) | PRODUCTION | Brain memory-layer.js |
| Importance decay | PLANNED | Week 4 — hourly tokio background task |
| fastembed semantic search | PLANNED | Week 4 — replace LIKE search |
| pgvector PgMemoryStore | PLANNED | Week 4 — sovereign Supabase `tssfdlodjgtedsssfpfc` |
| Memory consolidation endpoint | PLANNED | Week 4 — requires semantic search |
| Probation queue | DESIGNED | Defined in MEMORY_CONSTITUTION.md; not yet implemented |
| Contradiction detection | DESIGNED | Defined in MEMORY_CONSTITUTION.md; not yet implemented |

---

## Failure Modes

| Failure | Tag | Symptom |
|---------|-----|---------|
| Supabase down | RUNTIME_ENV | Memory writes fail; falls back to local SQLite |
| SQLite corrupted | RUNTIME_ENV | Local cache unavailable; all retrieval fails |
| Missing provenance fields | MEMORY | Write rejected at validation |
| fastembed index mismatch | RETRIEVAL | Semantic search returns wrong results |
| sqlx migration failure | RUNTIME_ENV | Memory store won't initialize |

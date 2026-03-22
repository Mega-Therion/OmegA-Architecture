# Roadmap — Week 4

**Author:** Gemini (Strategy & Operations)
**Date:** 2026-03-08
**Input:** ROADMAP_WEEK3.md, MEMORY_ARCHITECTURE.md, BENCHMARKS_GATEWAY.md (Week 3 results), SPRINT_SUMMARY_WEEK3.md

Every item has: What / Why / DoD / Effort / Dependencies.

---

## Priority Order

| # | Item | Effort | Depends on |
|---|------|--------|-----------|
| 1 | Semantic memory search (fastembed-rs) | L | Week 3 schema migration |
| 2 | Importance decay background task | S | Semantic search (for tier logic) |
| 3 | Contradiction detection on write | M | Semantic search |
| 4 | Memory consolidation endpoint (real) | M | Contradiction detection |
| 5 | Supabase/pgvector backend | M | Week 4 items 1–4 stable |
| 6 | Hard cutover — Rust as primary systemd service | S | 48h parallel-run complete |
| 7 | omega-cli shell completions | S | None |

---

## Item 1 — Semantic Memory Search (fastembed-rs)

**What:** Replace the SQLite LIKE-based keyword search in `SqliteMemoryStore` with cosine similarity over stored vector embeddings. Use `fastembed-rs` with the `all-MiniLM-L6-v2` model (384 dimensions, ~23 MB, downloads to `~/.omega/models/fastembed/` on first use). Add `embedding BLOB` column to `memory_entries` via migration `0002_add_embedding.sql`.

**Why:** Keyword search produces false negatives on paraphrase queries — "how long before consensus gives up" does not match "DCBFT timeout is 5 seconds." Semantic search makes memory retrieval actually useful for multi-turn conversations and context injection. This is the capability that justifies everything else in the memory stack.

**DoD:**
```bash
# Write two semantically distinct entries
curl -s -X POST http://localhost:8787/api/v1/memory/upsert \
  -H "Content-Type: application/json" \
  -d '{"content": "The DCBFT consensus timeout is 5 seconds", "namespace": "test"}'

curl -s -X POST http://localhost:8787/api/v1/memory/upsert \
  -H "Content-Type: application/json" \
  -d '{"content": "The Telegram bot reconnects every 30 seconds", "namespace": "test"}'

# Query with a paraphrase — must return DCBFT entry, not Telegram
curl -s -X POST http://localhost:8787/api/v1/memory/query \
  -H "Content-Type: application/json" \
  -d '{"query": "how long before the consensus protocol times out", "namespace": "test", "k": 1}'
# Expected: hits[0].content contains "DCBFT" AND score > 0.5
```

Unit tests that must pass:
- `test_semantic_search_finds_related_content` (embeddings feature enabled)
- `test_keyword_fallback_when_no_embedding` (works regardless of feature flag)

**Effort:** L — fastembed-rs links against ONNX Runtime via C FFI. Build may require GLIBC/libonnxruntime resolution. Graceful degradation to keyword search is a hard requirement if ONNX build fails.

**Dependencies:** Week 3 SQLite schema must be on disk (`migrations/0001_init.sql` applied). Migration `0002_add_embedding.sql` is new this week.

---

## Item 2 — Importance Decay Background Task

**What:** A `tokio::spawn`'d task that runs every 6 hours. Applies `importance *= 0.995` per hour (approximately) to entries in `Working` and `Session` tiers older than 7 days. Drops entries with `importance < 0.01` from search results (not deleted — importance below threshold is a soft filter). Logs row count at `tracing::debug!`. Half-life: ~6 days.

**Why:** Without decay, the memory store grows unbounded and old low-value entries crowd out recent high-value ones. Decay is the simplest bounded-memory strategy that requires no external coordination.

**DoD:**
```rust
// Unit tests in omega-memory/tests/decay_test.rs — all must pass:
test_decay_reduces_importance_for_old_entries   // entry at (now - 8d): importance drops from 1.0 to 0.98
test_decay_does_not_affect_episodic_entries     // Episodic tier is exempt
test_decay_does_not_affect_recent_entries       // < 7 days old = no decay applied
```

**Effort:** S — the background task is a simple Tokio interval loop + SQL UPDATE. The only coordination point is the `memory_tier` column (needed to exempt Episodic), which must be in place from Item 1's migration.

**Dependencies:** Item 1 (schema migration adds `memory_tier` column).

---

## Item 3 — Contradiction Detection on Write

**What:** On `POST /api/v1/memory/upsert`, embed the incoming content and search for existing entries with cosine similarity > 0.85. If found: write the new entry anyway, tag both entries with `contradiction_detected: true` in the `meta` JSON column, and return a `contradiction` object in the response. Change `MemoryStore::write()` return type from `MemoryId` to `MemoryWriteResult` enum.

The `MemoryWriteResult` enum:
```rust
pub enum MemoryWriteResult {
    Written(MemoryId),
    Contradiction {
        new_id: MemoryId,
        conflicting_ids: Vec<MemoryId>,
        conflicting_contents: Vec<String>,
        similarity: f32,
    },
}
```

Threshold is configurable via `OMEGA_MEMORY_CONTRADICTION_THRESHOLD` (default 0.85).

**Why:** Without contradiction detection, the memory store accumulates conflicting beliefs silently. When the gateway injects multiple contradictory memory hits into an LLM prompt, the LLM produces inconsistent or hedging responses. Surfacing contradictions lets the consolidation endpoint resolve them and keeps the context window coherent.

**DoD:**
```bash
# Write first entry
curl -s -X POST http://localhost:8787/api/v1/memory/upsert \
  -d '{"content": "The consensus timeout is 5 seconds", "namespace": "test"}'

# Write semantically near-duplicate — should trigger contradiction
curl -s -X POST http://localhost:8787/api/v1/memory/upsert \
  -d '{"content": "The consensus timeout is 10 seconds", "namespace": "test"}'
# Expected response: {"id": "...", "contradiction": {"conflicting_ids": [...], "similarity": > 0.85}}
```

Unit tests:
- `test_contradiction_detected_above_threshold`
- `test_no_contradiction_below_threshold`
- `test_both_entries_written_on_contradiction`

**Effort:** M — requires coordination with Codex: the `write()` trait signature change is breaking for all callers (gateway memory route handlers). Must be batched with any other trait changes this week to minimize churn.

**Dependencies:** Item 1 (needs embeddings to compute similarity scores).

---

## Item 4 — Memory Consolidation Endpoint (Real Implementation)

**What:** The stub `POST /api/v1/memory/consolidate` from Week 3 becomes a real synchronous operation. Three operations selectable via request body:
- `resolve_contradictions: true` — finds all pairs tagged `contradiction_detected: true` in the namespace, keeps the higher-confidence entry, archives the other.
- `promote_tiers: true` — runs Working→Session and Session→Episodic promotion rules immediately.
- `apply_decay: true` — runs importance decay immediately for the namespace.

Returns `ConsolidateResult` with counts for each operation and `duration_ms`.

**Why:** The background task runs every 6 hours. Manual consolidation is needed during development, after bulk imports, and when an operator spots contradictions in the logs and wants to resolve them without waiting for the next cycle. The endpoint makes the memory system operator-friendly.

**DoD:**
```bash
curl -s -X POST http://localhost:8787/api/v1/memory/consolidate \
  -H "Content-Type: application/json" \
  -d '{"namespace": "default", "resolve_contradictions": true, "promote_tiers": true, "apply_decay": false}'
# Expected HTTP 200:
# {
#   "consolidation_id": "cns_...",
#   "namespace": "default",
#   "contradictions_resolved": <int>,
#   "promotions": {"working_to_session": <int>, "session_to_episodic": <int>},
#   "decay_applied": false,
#   "duration_ms": <int>
# }
```

Unit test: `test_consolidate_resolves_contradictions` — write two near-identical entries, call consolidate with `resolve_contradictions: true`, assert one entry remains.

**Effort:** M — consolidation logic requires Items 1, 2, and 3 to be real (embeddings, decay, contradiction tagging). The HTTP handler is straightforward; the consolidation logic touches multiple subsystems.

**Dependencies:** Items 1, 2, 3.

---

## Item 5 — Supabase/pgvector Backend (PgMemoryStore)

**What:** Implement `PgMemoryStore` backed by the sovereign Supabase project (`tssfdlodjgtedsssfpfc`, URL: `https://tssfdlodjgtedsssfpfc.supabase.co`). The `MemoryStore` trait is already backend-agnostic. Wire via `OMEGA_DB_URL`:
- `sqlite:///path/to/file.db` → `SqliteMemoryStore` (current)
- `postgres://...` or `postgresql://...` → `PgMemoryStore`

Supabase has pgvector (`vector` extension) available. Embeddings column: `embedding vector(384)`. Queries use `1 - (embedding <=> query_embedding)` for cosine similarity (pgvector `<=>` operator).

The existing SQLite fire-and-forget sync becomes unnecessary once `PgMemoryStore` is the primary store — both gateway instances share the same Supabase database and memory is automatically consistent across restarts and instances.

**Why:** `SqliteMemoryStore` is single-node and single-file. It works for one developer. For distributed operation (two gateway instances, cross-session memory persistence to Supabase), the SQLite store is a workaround. `PgMemoryStore` is the correct production path.

**DoD:**
```bash
# Set OMEGA_DB_URL to the Supabase postgres URL
export OMEGA_DB_URL="postgresql://postgres:[password]@db.tssfdlodjgtedsssfpfc.supabase.co:5432/postgres"

# Start gateway — should use PgMemoryStore
OMEGA_DB_URL=$OMEGA_DB_URL cargo run --bin omega-gateway

# Write and query — same curl commands as Items 1–4
# Memory must persist across gateway restarts (SQLite does not survive a --clean)
```

Unit test: `test_pg_memory_store_write_and_search` — requires a test Supabase project or a local Postgres instance with pgvector.

**Effort:** M — `sqlx` supports both SQLite and Postgres feature flags. The schema difference (BLOB vs vector column, LIKE vs `<=>` operator) means the `search()` method needs a Postgres-specific implementation. The trait allows this cleanly.

**Dependencies:** Items 1–4 stable in `SqliteMemoryStore`. The Postgres implementation mirrors the SQLite one; ship SQLite first, then port.

---

## Item 6 — Hard Cutover: Rust as Primary systemd Service

**What:** If the 48h parallel-run shadow comparison (Rust on :8788) completes with no divergence from :8787, install the Rust binary as the authoritative systemd service on :8787. The Python venv remains archived but is not running.

Cutover script (requires sudo):
```bash
sudo cp /home/mega/OmegA-Sovereign/rust/omega-rust/omega-gateway.service.rust-ready \
    /etc/systemd/system/omega-gateway.service
sudo systemctl daemon-reload
sudo systemctl restart omega-gateway
curl -s http://127.0.0.1:8787/health  # must return {"ok":true}
```

**Note:** Based on the Week 3 benchmark session, both :8787 and :8788 are already running the Rust binary (`omega-gateway-rs`). The formal systemd cutover step is a paperwork/ownership step — the binary is already serving production. The cutover here means: confirm the service file points to the Rust binary and remove any Python fallback references.

**Why:** Closing the formal cutover loop. Having a Python fallback path that is not tested or maintained creates confusion about what is authoritative. One binary, one service file, one port.

**DoD:**
```bash
sudo systemctl status omega-gateway
# Active: active (running)
# ExecStart should reference /home/mega/bin/omega-gateway-rs

curl -s http://127.0.0.1:8787/health
# {"ok":true,"service":"Gateway","version":"0.1"}

journalctl -u omega-gateway --since "1 hour ago" | grep -i error
# No errors
```

**Effort:** S — the binary is already running. This is system administration + documentation update.

**Dependencies:** 48h parallel-run window verified (shadow :8788 behavior matches production :8787). This is already the case based on Week 3 session evidence.

---

## Item 7 — omega-cli Shell Completions

**What:** Add shell completions for bash, zsh, and fish via `clap_complete`. All 8+ subcommands (`ask`, `ask-claude`, `ask-gemini`, `briefing`, `pulse`, `chat`, `forward`, `gains`, `warp`) and their flags should autocomplete. Install script: `omega-cli completions bash > ~/.bash_completion.d/omega`.

**Why:** The CLI is used interactively every day. Tab completion reduces friction, prevents typos in subcommand names, and makes the tool discoverable for new users (including Mega, who types normally and doesn't use vim shortcuts).

**DoD:**
```bash
# Generate and source completions
omega-cli completions bash > /tmp/omega-completions.bash
source /tmp/omega-completions.bash

# Tab completion must work for subcommands
omega-cli <TAB>
# Expected: shows ask, ask-claude, ask-gemini, briefing, pulse, chat, forward, gains, warp

omega-cli ask --<TAB>
# Expected: shows --mode, --namespace, --temperature, etc.
```

**Effort:** S — `clap_complete` is a one-dependency addition. The completion generation is a single function call added to the CLI binary.

**Dependencies:** None. Can be done any day of Week 4.

---

## Three Open Decisions Carried from Week 3

### Decision 1 — Bridge Rewrite (omega-consensus crate)

**Status:** Still deferred. The criteria from ROADMAP_WEEK3.md hold:

Proceed with `omega-consensus` crate in Week 4 if:
1. The DCBFT protocol document is complete (it exists as Python source in `consensus_engine.py`)
2. The Python Bridge is showing reliability issues (it is not — it is running on :8000 without problems)
3. Claude has capacity after Items 1–4

Current verdict: **defer to Week 5.** The Python Bridge works. The Rust gateway memory stack is the value-delivering work for Week 4. Do not split focus.

Revisit trigger: if `bridge:8000` shows errors in `journalctl -u omega-workflows` or if a specific capability (e.g., faster DCBFT timeout) is blocked on Python speed.

### Decision 2 — gRPC

**Status:** Deferred. The Week 3 benchmark shows health p99 at 0.65ms. Inter-service HTTP/JSON overhead is not a bottleneck. This position holds until the system handles sustained 100+ concurrent users.

Revisit trigger: if `hey -c 100` throughput tests show the gateway becoming the bottleneck (rather than the LLM provider). Not expected at current scale.

### Decision 3 — Production Hardening (TLS, Logs, Circuit Breaker)

Week 4 is when the single-user Rust gateway becomes a hardened multi-session service. The scope:

1. **TLS termination** — via nginx reverse proxy (preferred over native rustls to keep the Rust binary deployment simple). nginx on :443 → Rust gateway on :8787 loopback.
2. **Structured log forwarding** — `tracing-subscriber` with JSON format → forward to `omega_events` table in Supabase sovereign project. Every request gets a `trace_id`; memory writes log `memory_id`; provider calls log `provider`, `latency_ms`, `tokens`.
3. **Health-based circuit breaker** — if a provider returns 3 consecutive 5xx or 429 in 60s, skip it in the failover chain for 5 minutes. Log the skip at `tracing::warn!`. This is a lightweight circuit breaker — no external state, implemented as an `Arc<Mutex<HashMap<ProviderId, Instant>>>` in `AppState`.

These are Week 4 engineering tasks for Codex. Gemini will verify and benchmark each one.

---

## Week 4 Definition of Done

All of the following must be true before Week 4 is called complete:

- [ ] `cargo test --workspace` passes with 0 failures
- [ ] Semantic search (Item 1): paraphrase query returns semantically relevant result, score > 0.5
- [ ] Decay (Item 2): `test_decay_reduces_importance_for_old_entries` passes
- [ ] Contradiction detection (Item 3): upsert response contains `contradiction` object when near-duplicate is written
- [ ] Consolidation (Item 4): `POST /api/v1/memory/consolidate` returns correct shape with real `contradictions_resolved` count
- [ ] PgMemoryStore (Item 5): gateway starts with `OMEGA_DB_URL=postgres://...` and memory persists across restart
- [ ] systemd service file references Rust binary (Item 6)
- [ ] `omega-cli completions bash` generates valid completion script (Item 7)
- [ ] `docs/BENCHMARKS_MEMORY.md` exists with memory write/query latency at 10k and 100k entries
- [ ] Week 4 production hardening (TLS, structured logs, circuit breaker) — at least one of the three implemented

---

*Trust, but verify. Automate, but log. Move fast, but don't break things.*

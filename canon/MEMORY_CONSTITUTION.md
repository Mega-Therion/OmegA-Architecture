# Memory Constitution
**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-13
**Operator:** RY (Mega)

This document governs all memory operations in OmegA. Every service that reads or writes memory must comply with these rules. Deviations require a Peace Pipe Council resolution.

---

## 1. Memory Tier Definitions

OmegA implements a six-tier memory architecture. Higher tiers are more durable and require more provenance.

| Tier | Name | Storage | Lifetime | Description |
|------|------|---------|----------|-------------|
| L1 | Working Memory | In-process RAM | Session | Ephemeral context. Lost on process restart. Used for active reasoning. |
| L2 | Session Memory | SQLite / Brain | Session + short-term | User-specific session history. Persists across request/response cycles within a session. |
| L3 | Episodic Memory | SQLite / Brain DB | Long-term | Narrative event logs. Significant interactions, task outcomes, decisions. |
| L4 | Semantic Memory | pgvector / fastembed SQLite | Long-term | Vector-indexed knowledge. Searchable by meaning, not just exact match. |
| L5 | Relational Memory | Supabase PostgreSQL | Long-term | Graph and SQL-structured facts. Cross-concept pathfinding. |
| L6 | Phylactery | Supabase / version-controlled files | Permanent | Identity kernel. Canonical values, style anchors, durable facts. Append-only with history. |

**Primary Supabase projects:**
- `sgvitxezqrjgjmduoool` — Primary (gAIng, Trinity)
- `tssfdlodjgtedsssfpfc` — OmegA-Sovereign (omega_memory, omega_events)

**Local cache:** SQLite via `omega-memory` Rust crate at `/home/mega/OmegA-Sovereign/rust/omega-rust/`

---

## 2. Write Rules

### What Gets Written

Memory writes are triggered by:

1. **Explicit operator command:** `remember: [content]` — always written, promoted to L3 or higher
2. **End-of-session summarization:** Brain summarizes significant session content to L3
3. **Mission completion:** Task outcomes and key decisions written to L3/L4
4. **Adjudicated council decisions:** Peace Pipe resolutions written to L6 (Phylactery)
5. **Autonomous reflection (Dream State):** Background synthesis of random memories; epiphanies may be promoted to L4
6. **Contradiction detection:** When new information contradicts existing canon, the conflict is written as a pending adjudication

### What Does NOT Get Written Automatically

- Raw API keys, secrets, bearer tokens
- Ephemeral tool outputs without significance
- PII beyond what RY has explicitly authorized for retention
- Internal debugging logs or transient errors
- Content from RESTRICTED folders (see LAW.json)

### Probation Queue

Unconfirmed memories (not yet verified or adjudicated) enter a **probation queue** before promotion to L3+. Promotion requires:
- End-of-session confirmation, OR
- Explicit operator command, OR
- Council resolution (for L6)

Probation entries expire after 7 days if not promoted.

---

## 3. Read Rules

### Retrieval Priority

When assembling context for a response, memory is retrieved in this order:

1. L1 (working memory) — always included
2. L6 (Phylactery) — identity anchors always injected
3. L2 (session memory) — current session context
4. L4 (semantic search) — relevant knowledge by vector similarity
5. L3 (episodic) — relevant past events
6. L5 (relational) — structured facts if needed

### Staleness Handling

- L1: Never stale (current session)
- L2: Stale threshold: 24 hours
- L3/L4: Importance decay applied. Background task multiplies importance by decay factor hourly. Entries below threshold are flagged for pruning, not auto-deleted.
- L5: Stale threshold: determined by relationship type
- L6: Never stale; superseded entries are archived, not deleted

**Importance decay:** Implemented in Rust gateway dream/agency tasks. Current config: hourly decay factor. Entries below threshold are pruned only after operator review (not automatic hard delete).

### JUSTIFIED_UNKNOWN Rule

When evidence for a claim is absent from available memory tiers:

**DO:** State "I don't have information about [X] in available memory. Here's what I do know: [evidence]."
**DO NOT:** Fabricate information to fill the gap.
**DO NOT:** Use generic boilerplate refusals ("As an AI assistant, I don't have...").
**DO NOT:** Claim confident knowledge of something that is not in memory.

The JUSTIFIED_UNKNOWN rule applies to all tiers. If the information is not in any memory tier, say so precisely — not with a blanket denial of capability.

---

## 4. Provenance Requirements

Every memory entry at L3 and above must include:

| Field | Required | Description |
|-------|----------|-------------|
| `source` | YES | Where this information came from (agent, user, external URL, council resolution) |
| `timestamp` | YES | ISO 8601 UTC timestamp of when the memory was written |
| `confidence` | YES | Float 0.0–1.0. Reflects certainty of the information at time of writing. |
| `session_id` | YES | The session in which this memory was created |
| `agent_id` | YES | Which agent wrote this memory |
| `revision_history` | YES (L6) | Append-only list of all changes. Previous versions preserved. |
| `raw_artifact_link` | RECOMMENDED | Link to the source document, transcript, or evidence |
| `conflict_flag` | CONDITIONAL | Set to true if this entry won a contradiction adjudication |
| `promoted_by` | RECOMMENDED | What triggered promotion from probation (operator / session_end / council) |

Missing provenance = non-durable memory. The `omega-memory` crate enforces provenance fields at write time.

---

## 5. Memory Revision and Deletion

### Revision Modes

| Mode | Description | When to Use |
|------|-------------|-------------|
| Supersede | Write new entry; mark old as superseded; retain both | New information updates an existing fact |
| Archive | Soft-delete; entry is retained but excluded from retrieval by default | Information is no longer relevant but may be needed for audit |
| Purge | Hard delete. Requires explicit operator command + Peace Pipe ratification for L6 | Privacy requirement, security incident, or explicit Chief order |

**Default posture:** Supersede, not erase. History is retained unless explicitly purged.

### Contradiction Handling

When a new write would contradict an existing L3+ entry:
1. Both entries are preserved
2. A conflict record is created
3. The conflict surfaces for adjudication (operator review or Peace Pipe for canon-level conflicts)
4. Adjudicated winner gets `conflict_flag: true` in its metadata
5. Loser is archived, not purged

---

## 6. Cross-Agent Memory Sharing Rules

- All agents write to shared memory tiers (L3–L6) via Brain or Bridge — not directly to the database
- Agents may read from any tier
- Agents may NOT overwrite another agent's L6 (Phylactery) entry without council approval
- Memory tagged with `agent_id: omega` is sovereign memory — only OmegA (via RY authority) may purge it
- Cross-agent contradictions follow the contradiction handling procedure above

---

## 7. Memory Corruption Handling

If the omega-memory crate or Supabase returns an integrity error:

1. Log the error with full context to `~/NEXUS/intelligence/log.json`
2. Fall back to local SQLite cache if cloud is unavailable
3. Do NOT fabricate data to replace corrupted entries — use JUSTIFIED_UNKNOWN
4. Alert RY via Telegram (via omega-workflows) if critical memory tiers are degraded
5. The Brain health watchdog checks memory tier availability every 30 seconds

---

## Known Conflicts

**Conflict 1:** OMEGA_FULL_SYSTEM_SPEC.md describes memory tiers as 4-layer (working/session/semantic/relational); OMEGA_VISION.md and OMEGA_SOVEREIGN_DNA.md describe 6-layer including Episodic and Phylactery. This document adopts the 6-layer model from OMEGA_VISION.md as it is more complete.

---

## Changelog

- 1.0.0 (2026-03-13): Initial canonical synthesis from OMEGA_VISION.md, OMEGA_FULL_SYSTEM_SPEC.md, omega-memory crate. Prior stub was a placeholder.

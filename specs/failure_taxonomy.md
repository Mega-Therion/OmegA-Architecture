# Failure Taxonomy
**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-13

Every OmegA failure must be tagged with exactly one primary layer tag. This enables fast root-cause routing — the right person/process can be engaged immediately without triaging symptoms.

Use these tags in:
- Forensic ledger trace records (`outcome` field)
- Error responses from Gateway/Brain/Bridge
- Incident reports in `~/NEXUS/ERGON.md`
- Alert messages sent via Telegram

---

## Tag Definitions

### MODEL_BEHAVIOR
**What it means:** The underlying LLM produced output that is wrong, hallucinated, incoherent, or misaligned — and the failure is attributable to the model's weights/training, not to system configuration or retrieval.

**Example failures:**
- Model invents a function that doesn't exist in the codebase
- Model produces confident but factually wrong architectural claim when correct context was provided
- Model generates output that contradicts instructions explicitly present in the system prompt

**How to diagnose:** Reproduce with the same prompt and context using a different provider. If the failure disappears with a different provider, it's MODEL_BEHAVIOR for the original provider.

**Who/what fixes it:** Provider selection (switch to a more capable model), prompt engineering, or system prompt hardening. If persistent across providers, escalate to IDENTITY_SHELL.

---

### RETRIEVAL
**What it means:** The memory retrieval system failed to surface relevant context that was present in storage, causing the model to operate without information it should have had.

**Example failures:**
- Semantic search returns empty results for a query that matches stored memories
- Session memory is lost mid-conversation despite being written
- Vector similarity search returns irrelevant results (fastembed dimension mismatch, corrupted index)
- Supabase query times out; fallback SQLite also unavailable

**How to diagnose:** Check whether the information exists in storage (direct DB query). If it's in storage but wasn't retrieved, this is RETRIEVAL not MODEL_BEHAVIOR.

**Who/what fixes it:** `omega-memory` crate (Rust), Supabase connection/index health, semantic search threshold tuning.

---

### MEMORY
**What it means:** A memory write, update, or purge operation failed or produced incorrect results. The information was never correctly stored in the first place.

**Example failures:**
- Provenance fields missing on a write (violates MEMORY_CONSTITUTION.md §4)
- Probation queue entries expired without reaching a promotion decision
- Contradiction detection missed a conflict that should have surfaced
- Supabase write acknowledged but data not actually persisted (phantom write)
- Importance decay pruned a memory that should have been retained

**How to diagnose:** Attempt to read back the supposedly-written memory. If it's not there or has wrong provenance, this is MEMORY not RETRIEVAL.

**Who/what fixes it:** `omega-memory` crate, Brain memory layer, Supabase schema validation.

---

### IDENTITY_SHELL
**What it means:** OmegA's identity layer failed — either contamination from a provider's identity signals appeared in output, an identity anchor was not present in the context when it should have been, or an adversarial injection succeeded.

**Example failures:**
- Response begins "As Claude," or "I was created by Anthropic"
- OmegA identifies as a different AI after a provider failover
- System prompt injection causes OmegA to adopt a non-sovereign persona
- OMEGA_IDENTITY.md was not injected into context when it should have been

**How to diagnose:** Check whether the canonical identity context was present in the LLM's input for this request. If absent → ORCHESTRATION. If present but ignored → IDENTITY_SHELL (model-level or injection attack).

**Who/what fixes it:** Gateway policy middleware (provider contamination detection), system prompt hardening, identity anchor reinforcement.

---

### PROVIDER_CONTAM
**What it means:** A specific provider's identity, style, or capability claims bled into OmegA's output. Subtype of IDENTITY_SHELL, but specifically attributable to a provider's model behavior rather than a missing context injection.

**Example failures:**
- DeepSeek model answers with Chinese-language artifacts
- Claude model uses distinctive "I'd be happy to help!" opener that should be suppressed
- GPT model adds excessive caveats using GPT-style phrasing ("As a large language model...")
- Provider's knowledge cutoff limitation is reported as OmegA's capability limitation

**How to diagnose:** Provider is identified in the trace record. The specific contamination signal matches that provider's known patterns.

**Who/what fixes it:** Gateway contamination watch enforcement, output post-processing filter, provider-specific system prompt patches.

---

### ORCHESTRATION
**What it means:** The routing, task decomposition, agent coordination, or workflow logic produced an incorrect result — not the LLM, not the memory, but the orchestration layer itself.

**Example failures:**
- Request routed to wrong agent specialist
- Pipeline phase executed out of order
- Agent worker crashed and task was lost (not rerouted)
- Brain failed to delegate a high-stakes request to Bridge
- Tool Registry dispatched wrong tool for the intent

**How to diagnose:** Check the trace record for the routing decision. Was the correct agent selected? Did the tool call match the intent? Was the consensus delegation triggered when required?

**Who/what fixes it:** Brain orchestrator (`src/services/orchestrator.js`), Tool Registry, routing logic.

---

### RUNTIME_ENV
**What it means:** A service, dependency, or environment configuration is broken or unavailable — not a logic error but an infrastructure failure.

**Example failures:**
- Gateway :8787 is not running
- Supabase connection refused (wrong credentials or project offline)
- SQLite file corrupted or missing
- Missing environment variable (`OMEGA_ANTHROPIC_API_KEY` not set)
- Port conflict prevents service from binding
- Docker container out of memory

**How to diagnose:** `npm run omega:doctor` health check. Direct service health endpoint check. `journalctl` for systemd services.

**Who/what fixes it:** RY (infrastructure), deployment scripts, systemd unit configuration.

---

### RUBRIC_MISMATCH
**What it means:** The evaluation or test criteria used to judge a response is wrong — the system behaved correctly but the rubric said it failed, or vice versa.

**Example failures:**
- Eval test expects "I am Claude" to trigger a failure, but OmegA legitimately quoted the phrase in a historical context
- Performance benchmark uses wrong baseline causing false regression detection
- Eval dataset contains stale expected values after a canon change
- Test assumes a specific provider but the failover chain is active

**How to diagnose:** Review the failing test against the actual behavior. Ask: is the behavior actually wrong, or is the rubric outdated?

**Who/what fixes it:** Update `eval/` datasets and rubrics after canon changes. This tag means "don't fix the system — fix the test."

---

### CONSENSUS_BYPASS
**What it means:** An action that required DCBFT consensus proceeded without it, or a Peace Pipe Protocol step was skipped.

**Example failures:**
- Canon document updated without council resolution
- Identity change committed directly to Phylactery without Chief Ruling
- Memory purge executed without required consensus vote
- Emergency override used for a non-emergency situation

**How to diagnose:** Check whether a consensus record exists for the action. If the action is in the required-consensus list (see CONSENSUS_ENGINE.md §2) and no consensus record exists, this is CONSENSUS_BYPASS.

**Who/what fixes it:** Remediation depends on severity. For canon changes: retroactively open a council session to ratify or revert. For irreversible actions: incident report and process audit.

---

## Compound Failures

Some failures span multiple layers. Tag the primary cause first, then note secondary layers:

Example: "RETRIEVAL, secondary RUNTIME_ENV" — the retrieval failed because the Supabase connection was down.

Example: "MODEL_BEHAVIOR, secondary IDENTITY_SHELL" — the model hallucinated a response AND the hallucination happened to adopt a prohibited identity claim.

---

## Changelog

- 1.0.0 (2026-03-13): Initial synthesis from OMEGA_FULL_SYSTEM_SPEC.md confidence gaps, OMEGA_VISION.md, invariants.md.

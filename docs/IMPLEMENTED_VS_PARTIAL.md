# OmegA v0.2 — Implemented vs Partial Capability Matrix

**Date:** 2026-03-25
**Scope:** Tickets 1–20

This document is the honest capability matrix. "Implemented" means code exists, tests pass, and the component does what is described. "Partial" means code exists but scope is limited. "Aspirational" means documented but not yet built.

---

## Fully Implemented

| Component | Location | Notes |
|-----------|----------|-------|
| AEGIS identity enforcement | `omega/aegis.py` | Name/role boundary checks pass |
| Capability registry + enforcement | `omega/capabilities.py` | Fail-closed, context-aware |
| Ingest plane with dedup detection | `omega/ingest.py` | Hash-based, version tracking |
| Provider abstraction (Ollama/OpenAI/Anthropic/Google) | `omega/providers/` | Waterfall fallback, key isolation |
| Hybrid retriever (lexical + semantic) | `omega/retrieval.py` | TF-IDF + cosine, multi-hop support |
| Answer builder with evidence grounding | `omega/answer.py` | grounded/inferred/abstained modes |
| Verifier (V-score, hedging detection) | `omega/verifier.py` | Heuristic-based, threshold configurable |
| Claim graph + evidence linking | `omega/claims.py` | Directed graph, contradiction detection, uncertainty propagation |
| Query planner + retrieval strategy | `omega/query_planner.py` | SIMPLE/MULTI_HOP/CONTRADICTION_AWARE/EXHAUSTIVE |
| Session continuity store | `omega/session.py` | Disk-persisted, crash recovery, resume |
| Task object model + state machine | `omega/tasks.py` | Legal transition enforcement, QUEUED→RUNNING→COMPLETED etc. |
| Planner/Executor split | `omega/planner.py`, `omega/executor.py` | Executor refuses unvalidated plans |
| Human approval queue | `omega/approvals.py` | Request/decision lifecycle, expiry |
| Policy DSL + loader | `omega/policy.py` | Custom YAML parser, validate() |
| Policy files (default, strict, local_dev) | `policies/` | All validate cleanly |
| Security + secret isolation | `omega/security.py` | SecretAccessor, Redactor, TrustBoundary |
| Telemetry + observability | `omega/telemetry.py` | Event emission, JSONL persistence, RunMetrics |
| Failure injection harness | `evals/failure_injection.py` | 7 modes, all deterministic |
| Adversarial eval corpus | `evals/adversarial/` | 15 cases across 4 categories |
| Baseline comparison framework | `evals/compare_baselines.py` | 4 baselines, 4 scoring dimensions |
| Real-world corpus | `evals/corpora/real_world/` | 20 tasks across 5 categories |
| Governed Research Copilot API | `web/src/app/api/research/route.ts` | Full 6-stage pipeline in TypeScript |
| Research UI | `web/src/components/ResearchPanel/`, `web/src/app/research/page.tsx` | Evidence display, mode badge, trace toggle |

---

## Partial / Limited Scope

| Component | What Exists | What's Missing |
|-----------|-------------|----------------|
| Verifier | Heuristic V-score (keyword patterns, coverage) | Model-based NLI verifier |
| Policy YAML parser | Handles flat key-value, list, one-level nested | Full YAML spec (multiline strings, anchors, etc.) |
| Real-world corpus runner | Corpus JSON files + structure | Automated runner connecting corpus → OmegA pipeline |
| Approval UI | API backend complete | No web UI for approve/reject actions |
| Session UI | Backend session store complete | No UI to browse/resume sessions from the Research page |
| Multi-hop retrieval | execute_plan() dispatches multi-hop strategy | Second-hop re-retrieval uses simpler query expansion |

---

## Aspirational (Documented, Not Yet Built)

| Item | Reference |
|------|-----------|
| Encryption at rest for session files | `docs/SECURITY_MODEL.md` |
| mTLS between components | `docs/SECURITY_MODEL.md` |
| Hardware security module integration | `docs/SECURITY_MODEL.md` |
| Fine-grained RBAC for approval decisions | `docs/SECURITY_MODEL.md` |
| Model-based NLI verifier | Future upgrade path |
| Streaming verifier (token-by-token) | Future upgrade path |
| Persistent graph store (Neo4j / RDF) | ClaimGraph is currently in-memory |
| Cross-session claim graph merging | Sessions are currently isolated |

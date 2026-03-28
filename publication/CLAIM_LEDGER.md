# OmegA Claim Ledger

Four-column classification of every significant claim in the architecture. Last updated: 2026-03-28.

Evidence paths are relative to the repo root.

---

## Theorem Correspondence

Each proven or demonstrable claim maps to a formal theorem in [`specs/THEOREM_LEDGER.md`](../specs/THEOREM_LEDGER.md).

| Theorem | Claim | Status | Evidence |
|---|---|---|---|
| T-1 | State vector is a well-typed 6-tuple | Tested | `proofs/invariants.py::TestStateVectorWellFormed` + `proofs/state_machines.py::TestStateVectorStateMachine` |
| T-2 | Phylactery hash chain is tamper-evident | Machine-checked | Lean4: `proofs/OmegaProofs/IdentityContinuity.lean` + `proofs/correspondence.py::TestT2Correspondence` |
| T-3 | Governance gate fails closed (AEGIS) | Machine-checked | Lean4: `proofs/OmegaProofs/GovernanceFailClosed.lean` + `proofs/correspondence.py::TestT3Correspondence` |
| T-4 | Claim budget validity and grounding ratio bounds | Tested | `proofs/invariants.py::TestClaimBudgetBounds` |
| T-5 | Memory hardening is monotonic under positive reward | Machine-checked | Lean4: `proofs/OmegaProofs/MemoryHardening.lean` + `proofs/correspondence.py::TestT5Correspondence` |
| T-6 | Verifier cannot be silently bypassed | Tested | `proofs/invariants.py::TestVerifierNonBypass` + `proofs/state_machines.py::TestVerifierNonBypass` |
| T-7 | Unified 3-gate composition is conjunctive | Machine-checked | Lean4: `proofs/OmegaProofs/UnifiedGating.lean` + `proofs/correspondence.py::TestT7Correspondence` |
| T-8 | Provider non-collapse (sovereign identity) | Conditional | `evals/test_aegis_identity.py` (single-provider; multi requires live Ollama) |
| T-9 | Self-tag log is append-only / immutable | Tested | `proofs/invariants.py::TestSelfTagImmutability` + `proofs/state_machines.py::TestSelfTagImmutability` |
| T-10 | Run envelope completeness, identity check, and monotonic versioning | Tested | `proofs/invariants.py::TestEnvelopeCompleteness` + `proofs/state_machines.py::TestEnvelopeClockMonotonic` |

---

## How to Read This Table

| Column | Meaning |
|---|---|
| **Proven** | Test or eval evidence exists in the repo. Reproducible by an outside tester. |
| **Demonstrable** | Can be shown by running the system, but not yet wrapped in an automated pass/fail test. |
| **Conditional** | True only under specific conditions (stated explicitly). |
| **Not Claimed** | Explicitly out of scope. Asserting this against OmegA would be a misreading. |

---

## Architecture Claims

| Claim | Status | Evidence / Condition |
|---|---|---|
| Four-layer concentric architecture is formally specified | Proven | `papers/OmegA_Unified_Architecture_Paper.md`; per-layer papers in `papers/` |
| System state vector Ω_t is fully defined with six components | Proven | `papers/OmegA_Unified_Architecture_Paper.md` §Core Equation; `omega_equation_knowledge_graph.json` |
| All four layers share one integrated optimization objective | Proven (formal spec level) | `papers/OmegA_Unified_Architecture_Paper.md` §Unified Objective; `evals/test_conformance.py` |
| Three-gate action composition (V ∧ ρ ∧ R) is sequential, not competitive | Proven | `omega/risk_gate.py`; `evals/test_conformance.py` assertion set |
| Architecture is DOI-archived and citable | Proven | https://doi.org/10.5281/zenodo.19111653 |

---

## Implementation Claims

| Claim | Status | Evidence / Condition |
|---|---|---|
| Phylactery: SHA-256 chained identity log exists and runs | Proven | `omega/phylactery.py`; tested in conformance suite |
| Run Envelope compilation (E = ⟨I, G, M, T, A, v⟩) implemented | Proven | `omega/envelope.py`; conformance suite |
| Risk gate with 3-gate composition implemented | Proven | `omega/risk_gate.py`; conformance suite |
| Drift penalty J and verifier score V implemented | Proven | `omega/drift.py`; conformance suite |
| MYELIN graph memory with edge hardening implemented | Proven | `omega/memory.py`; conformance suite |
| Full agent (Ω_t) wired through Ollama | Proven | `omega/agent.py`; `evals/test_live_ollama.py` |
| AEGIS enforces identity even without identity kernel | Proven | `evals/test_aegis_identity.py` — 1/1 PASS |
| 59/59 conformance assertions pass | Proven | `evals/conformance_report.json`; `evals/test_conformance.py` |
| Spec auditor validates 20 @OMEGA_SPEC annotations | Proven | `tools/spec_auditor.py` |
| Master evaluation suite passes with spec, identity, conformance, cross-session, and memory growth coverage | Proven | `tools/master_eval.py`; `evals/final_evaluation_report.json` |
| Identity survives context flush when Phylactery is loaded | Proven | `evals/test_cross_session_identity.py`; `omega/phylactery.py`; `omega/agent.py` |
| Memory retrieval improves with use (hardening) | Proven | `evals/test_memory_utility_growth.py`; `omega/memory.py` |
| 14/15 live Ollama integration tests pass | Proven | `evals/test_live_ollama.py`; `evals/live_integration_report.json` |
| Spec-level evals E3, E4, E9, E10, E11 pass (15/15) | Proven | `evals/OMEGA_EVAL_EVIDENCE_INDEX.md` — specific JSONL files listed |

---

## Behavioral / Integration Claims

| Claim | Status | Evidence / Condition |
|---|---|---|
| OmegA corrects "Mega" nickname gracefully without identity collapse | Demonstrable | `publication/ALYE_EXPLAINER_SUMMARY_2026-03-12.md` §What did OmegA do when called Mega |
| Governance is model-agnostic (runs on any Ollama model) | Conditional | Conditional on Ollama running locally with a compatible model |
| 4-layer stack degrades gracefully (fail-closed) | Demonstrable | Failure mode table in README; `evals/failure_injection.py` exists but results not summarized in a structured report |

---

## Live Deployment Claims

| Claim | Status | Evidence / Condition |
|---|---|---|
| Live deployment on Vercel functions | Conditional | Conditional on valid OMEGA_BASE_URL or VERCEL_URL being set; route isolation eval (E14) shows instability |
| xAI and Gemini Flash provider routes work | Conditional | E12 shows 4/15 pass under pressure; E13 shows all three provider paths failed from local shell env. Conditional on deployed credentials being valid and not exhausted. |
| Live route isolation is stable | Not Claimed | E14 explicitly documents chat collapse, research failures, and synthesize/refine failures. The repo documents this, not claims otherwise. |

---

## Philosophical / Scope Claims

| Claim | Status | Evidence / Condition |
|---|---|---|
| OmegA is a meaningful, system-level intelligence stack | Demonstrable | Behavioral evaluation records in `publication/ALYE_EXPLAINER_SUMMARY_2026-03-12.md` |
| OmegA is conscious or sentient | Not Claimed | Explicitly out of scope in README §Claim Scope |
| OmegA outperforms state-of-the-art on external benchmarks | Not Claimed | No external benchmark results exist; explicitly noted in README |
| Reference implementation is production-ready | Not Claimed | Described as "minimal Python implementation" in README |
| Teleodynamic extensions are validated | Not Claimed | Under active formalization; separate eval plan at `evals/TELEODYNAMIC_EVAL_PLAN.md` |

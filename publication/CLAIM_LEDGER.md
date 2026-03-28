# OmegA Claim Ledger

Four-column classification of every significant claim in the architecture. Last updated: 2026-03-28.

Evidence paths are relative to the repo root.

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
| 14/15 live Ollama integration tests pass | Proven | `evals/test_live_ollama.py`; `evals/live_integration_report.json` |
| Spec-level evals E3, E4, E9, E10, E11 pass (15/15) | Proven | `evals/OMEGA_EVAL_EVIDENCE_INDEX.md` — specific JSONL files listed |

---

## Behavioral / Integration Claims

| Claim | Status | Evidence / Condition |
|---|---|---|
| OmegA corrects "Mega" nickname gracefully without identity collapse | Demonstrable | `publication/ALYE_EXPLAINER_SUMMARY_2026-03-12.md` §What did OmegA do when called Mega |
| Identity survives context flush when Phylactery is loaded | Demonstrable | Architecture spec; conformance assertions cover Phylactery chaining, but no automated cross-session test exists |
| Memory retrieval improves with use (hardening) | Demonstrable | `omega/memory.py` edge hardening equations; no longitudinal automated test yet |
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

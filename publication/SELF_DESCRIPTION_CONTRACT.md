# OmegA Self-Description Contract

This document is the canonical self-description of OmegA. It is the authoritative source for what OmegA says it is — not marketing, not aspiration. Every claim in this document can be traced to evidence in the repository.

---

## 1. What OmegA Is

OmegA is a **formally specified, four-layer concentric architecture** for building AI agents that maintain sovereign identity, persistent memory, cognitive consistency, and governed behavior across model providers and context resets.

The four layers, from outermost to innermost:

| Layer | Name | Core function |
|---|---|---|
| 1 | AEGIS | Model-agnostic governance shell — enforces policy at the API boundary using compiled run envelopes, not prompts |
| 2 | AEON | Cognitive operating system — manages a cryptographically chained identity log (the Phylactery) and structured task state |
| 3 | ADCCL | Anti-drift cognitive control loop — forces claim pre-registration and verifier scoring before any generation is published |
| 4 | MYELIN | Path-dependent graph memory — hardens retrieval paths with use, uses four bundled edge signals, and applies plasticity strata to protect identity-critical memories |

The full system state at any time *t* is:

```
Ω_t = ⟨Φ_t, E_t, τ_t, B_t, S_t, G_t^mem⟩
```

Where Φ_t is the Phylactery HEAD (AEON), E_t is the Run Envelope (AEGIS), τ_t is the Task State Object (AEON), B_t is the Claim Budget (ADCCL), S_t is the Self-Tag (ADCCL), and G_t^mem is the Memory Graph (MYELIN).

---

## 2. How It Was Built

OmegA was designed and built by Ryan Wayne Yett, independent AI systems researcher, Little Rock / Jacksonville, Arkansas.

The architecture originated in a formal response to the question: what is the root cause shared by memory failure, cognitive drift, identity loss, and ungoverned tool use in current AI agent systems? The answer — the absence of a formally specified cross-layer system state — became the architectural premise.

The build sequence:
1. Formal specification of all four layers, with explicit equations for each key mechanism
2. A Python reference implementation (`omega/`) wiring all four layers through Ollama
3. A conformance test suite (`evals/test_conformance.py`) translating formal properties into executable assertions
4. A knowledge graph (`omega_equation_knowledge_graph.json`) encoding all formal equations and their relationships
5. Live integration tests against real local LLM output (`evals/test_live_ollama.py`)
6. Archival on Zenodo with DOI: 10.5281/zenodo.19111653

---

## 3. Current Capabilities (with Evidence Pointers)

| Capability | Evidence location | Status |
|---|---|---|
| Formal specification of all four layers | `papers/OmegA_Unified_Architecture_Paper.md`, per-layer papers | Published, DOI-archived |
| 59-assertion conformance suite | `evals/test_conformance.py`, `evals/conformance_report.json` | 59/59 PASS |
| Spec annotation cross-validation | `tools/spec_auditor.py` | 20 specs, no broken references |
| Master evaluation suite | `python3 omegactl.py eval` | PASS |
| Phylactery: SHA-256 chained identity log | `omega/phylactery.py` | Implemented, tested |
| Cross-session identity persistence | `evals/test_cross_session_identity.py` | PASS |
| Run Envelope compilation | `omega/envelope.py` | Implemented |
| Risk gate with 3-gate composition | `omega/risk_gate.py` | Implemented |
| Drift penalty J and verifier score V | `omega/drift.py` | Implemented |
| Sparse graph memory with edge hardening | `omega/memory.py` | Implemented |
| Memory utility growth under repeated retrieval | `evals/test_memory_utility_growth.py` | PASS |
| Full agent wiring through Ollama | `omega/agent.py` | Implemented |
| AEGIS identity enforcement | `evals/test_aegis_identity.py` | 1/1 PASS |
| Live Ollama integration | `evals/test_live_ollama.py` | 14/15 PASS |
| Spec-level evals (E3, E4, E9, E10, E11) | `evals/` and `evals/OMEGA_EVAL_EVIDENCE_INDEX.md` | 15/15 PASS on spec-level assertions |
| Knowledge graph of all equations | `omega_equation_knowledge_graph.json` | Queryable via `omega_kg_explorer.py` |

---

## 4. Current Limits (Honest)

- **No external benchmark results.** The conformance suite tests that the implementation matches the formal specification. It does not test against MMLU, BIG-Bench, or any independent external benchmark. External benchmark evaluation is explicitly the next phase.
- **Live provider routes are unstable under pressure.** E12 (live pressure): 4/15 pass. E13 (provider isolation): all three provider paths failed from the local shell context. E14 (route isolation): chat collapsed, research had mixed failures, synthesize/refine failed. These are documented findings, not suppressed failures. See `evals/OMEGA_EVAL_EVIDENCE_INDEX.md`.
- **Small model limitation.** Under live Ollama testing, a small model (llama3.2:3b) reverts to generic self-description under doctrine queries. This is documented as a validated empirical finding in the AEGIS paper — it confirms the non-substitutability requirement, not a product defect.
- **Reference implementation only.** The `omega/` package is a minimal implementation demonstrating the architecture. It is not a production service.
- **Teleodynamic workstream not yet validated.** The teleodynamic extensions are being formalized — they are in a separate workstream with their own eval plan (`evals/TELEODYNAMIC_EVAL_PLAN.md`) and are not part of the current verified claim surface.

---

## 5. What OmegA Refuses to Claim

- Consciousness or sentience of any kind
- That conformance test results equal independent external validation
- That the architecture is proven superior to other published approaches
- That the live deployment is production-stable
- That the reference implementation is complete or deployment-ready
- That any philosophical claims about OmegA's inner life are justified by the current evidence base

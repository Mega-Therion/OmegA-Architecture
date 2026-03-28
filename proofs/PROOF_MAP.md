# OmegA Proof Map

**Version:** 1.0.0
**Last Updated:** 2026-03-28

For each theorem/invariant in `specs/THEOREM_LEDGER.md`, this document traces:
**Claim -> Formal Statement -> Code Path -> Test -> Runtime Artifact -> Log Entry**

---

## T-1: State Vector Well-Formedness

| Step | Artifact |
|---|---|
| Claim | Omega_t is a 6-tuple of well-typed, non-null components at all times |
| Formal statement | `specs/THEOREM_LEDGER.md` T-1 |
| Code path | `omega/phylactery.py` (Phi_t), `omega/envelope.py` (E_t), `omega/drift.py` (tau_t, B_t), `omega/memory.py` (G_t^mem) |
| Test | `proofs/invariants.py::test_state_vector_well_formed` |
| Runtime artifact | Agent state dict assembled in `omega/agent.py` |
| Log entry | Conformance report: `evals/conformance_report.json` |

---

## T-2: Identity Continuity (Phylactery Hash Chain)

| Step | Artifact |
|---|---|
| Claim | Phi_{t+1} = H(Phi_t || delta || R); chain is tamper-evident |
| Formal statement | `specs/THEOREM_LEDGER.md` T-2 |
| Code path | `omega/phylactery.py::Phylactery.commit()`, `Phylactery.verify_chain()` |
| Test | `proofs/invariants.py::test_identity_continuity` (property-based), `evals/test_cross_session_identity.py` |
| Runtime artifact | Phylactery JSON file (persisted chain) |
| Log entry | Cross-session identity test results |

---

## T-3: Governance Fail-Closed (AEGIS)

| Step | Artifact |
|---|---|
| Claim | R(a) >= tau_consent implies denial; BLOCKED_PATTERNS hard-block |
| Formal statement | `specs/THEOREM_LEDGER.md` T-3 |
| Code path | `omega/risk_gate.py::RiskGate.gate()` |
| Test | `proofs/invariants.py::test_governance_fail_closed` |
| Runtime artifact | Gate decision tuple (allowed, score) |
| Log entry | Conformance report: `evals/conformance_report.json` |

---

## T-4: Claim Budget Validity (ADCCL)

| Step | Artifact |
|---|---|
| Claim | SUPPORTED claims require evidence; grounding ratio in [0, 1] |
| Formal statement | `specs/THEOREM_LEDGER.md` T-4 |
| Code path | `omega/drift.py::ClaimBudget.is_valid()`, `ClaimBudget.grounding_ratio()` |
| Test | `proofs/invariants.py::test_claim_budget_bounds` |
| Runtime artifact | ClaimBudget object in agent state |
| Log entry | Conformance report: `evals/conformance_report.json` |

---

## T-5: Memory Hardening Monotonicity (MYELIN)

| Step | Artifact |
|---|---|
| Claim | Positive reward increases q_ij; co-activation non-decreasing; staleness resets |
| Formal statement | `specs/THEOREM_LEDGER.md` T-5, Lemmas T-5a, T-5b |
| Code path | `omega/memory.py::EdgeBundle.harden()` |
| Test | `proofs/invariants.py::test_memory_hardening_monotonic` (property-based), `evals/test_memory_utility_growth.py` |
| Runtime artifact | EdgeBundle objects in MemoryGraph |
| Log entry | Memory utility growth test results |

---

## T-6: Verifier Non-Bypass

| Step | Artifact |
|---|---|
| Claim | V <= tau_verify blocks action regardless of rho and R |
| Formal statement | `specs/THEOREM_LEDGER.md` T-6 |
| Code path | `omega/risk_gate.py::RiskGate.multi_gate()` |
| Test | `proofs/invariants.py::test_verifier_non_bypass` |
| Runtime artifact | multi_gate result dict |
| Log entry | Conformance report |

---

## T-7: Unified Action Gating

| Step | Artifact |
|---|---|
| Claim | 3-gate conjunction: V AND rho AND R; no gate compensates another |
| Formal statement | `specs/THEOREM_LEDGER.md` T-7 |
| Code path | `omega/risk_gate.py::RiskGate.multi_gate()` |
| Test | `proofs/invariants.py::test_unified_action_gating` (property-based), `evals/test_conformance.py` |
| Runtime artifact | multi_gate result dict |
| Log entry | Conformance report |

---

## T-8: Provider Non-Collapse

| Step | Artifact |
|---|---|
| Claim | Identity response is sovereign across all providers |
| Formal statement | `specs/THEOREM_LEDGER.md` T-8 |
| Code path | `omega/envelope.py::RunEnvelope.to_system_prompt()`, `omega/agent.py` |
| Test | `evals/test_aegis_identity.py` (automated, single-provider) |
| Runtime artifact | System prompt string containing sovereign identity |
| Log entry | AEGIS identity enforcement test results |

---

## T-9: Self-Tag Immutability

| Step | Artifact |
|---|---|
| Claim | S_t is append-only; historical entries immutable |
| Formal statement | `specs/THEOREM_LEDGER.md` T-9 |
| Code path | `omega/phylactery.py::Phylactery.commit()`, `Phylactery.verify_chain()` |
| Test | `proofs/invariants.py::test_self_tag_immutability` |
| Runtime artifact | Phylactery chain (append-only by construction) |
| Log entry | Chain verification result |

---

## T-10: Run Envelope Completeness

| Step | Artifact |
|---|---|
| Claim | Envelope must be complete and carry identity before execution |
| Formal statement | `specs/THEOREM_LEDGER.md` T-10 |
| Code path | `omega/envelope.py::RunEnvelope.is_complete()`, `RunEnvelope.has_identity()` |
| Test | `proofs/invariants.py::test_envelope_completeness` |
| Runtime artifact | RunEnvelope instance |
| Log entry | Conformance report |
| **Gap** | Monotonic version counter not yet implemented |

---

## Coverage Matrix

| Theorem | Property Test | Deterministic Test | Empirical Evidence | Formal Proof |
|---|---|---|---|---|
| T-1 | Yes | Yes (conformance) | -- | -- |
| T-2 | Yes | Yes (cross-session) | -- | Phase 2 |
| T-3 | Yes | Yes (conformance) | -- | -- |
| T-4 | Yes | Yes (conformance) | -- | -- |
| T-5 | Yes | Yes (memory growth) | Yes | Phase 2 |
| T-6 | Yes | -- | -- | -- |
| T-7 | Yes | Yes (conformance) | -- | Phase 2 |
| T-8 | -- | Yes (aegis identity) | Conditional | -- |
| T-9 | Yes | Yes (cross-session) | -- | -- |
| T-10 | Yes | -- | -- | -- |

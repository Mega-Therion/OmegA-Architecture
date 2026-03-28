# OmegA Theorem Ledger

**Version:** 1.1.0
**Status:** CANONICAL
**Last Updated:** 2026-03-28

This ledger upgrades the Claim Ledger to academic-grade classification. Every significant architectural claim is formally stated and assigned one of:

| Type | Meaning |
|---|---|
| **Theorem** | Formally stated, proof required |
| **Lemma** | Supporting formal statement used by a theorem |
| **Executable Invariant** | Tested by code (property-based or deterministic) |
| **Empirical Claim** | Backed by measured data from evaluation runs |
| **Conditional Claim** | True only under explicitly stated conditions |
| **Out-of-Scope** | Explicitly not claimed by OmegA |

Evidence status legend:

| Status | Meaning |
|---|---|
| **Proven** | Formal proof or exhaustive test exists |
| **Tested** | Property-based or deterministic test passes |
| **Gap** | Claim is stated but evidence is incomplete |

---

## T-1: State Vector Well-Formedness

**Classification:** Executable Invariant

**Formal Statement:**
For all time steps t, the system state vector is a 6-tuple of well-typed, non-null components:

```
Omega_t = <Phi_t, E_t, tau_t, B_t, S_t, G_t^mem>
```

where:
- Phi_t is a 64-character hex string (SHA-256 hash)
- E_t is a RunEnvelope with all REQUIRED_FIELDS non-null
- tau_t is a GoalContract with non-empty task field
- B_t is a ClaimBudget (possibly empty list, but valid)
- S_t is an append-only list of self-tag entries
- G_t^mem is a MemoryGraph instance

**Code path:** `omega/phylactery.py`, `omega/envelope.py`, `omega/drift.py`, `omega/memory.py`
**Test:** `proofs/invariants.py::TestStateVectorWellFormed`
**State machine:** `proofs/state_machines.py::TestStateVectorStateMachine` — 7 invariants checked across randomized transitions
**Paper:** `papers/OmegA_Unified_Architecture_Paper.md` -- Core Equation
**Evidence status:** Tested (property-based + stateful state machine)

---

## T-2: Identity Continuity (Phylactery Hash Chain)

**Classification:** Theorem

**Formal Statement:**
The Phylactery identity chain satisfies:

```
Phi_{t+1} = H(Phi_t || delta || R)
```

Specifically: for all commits i > 0 in the chain, `commit[i].hash == SHA256(commit[i].parent_hash + commit[i].content)` and `commit[i].parent_hash == commit[i-1].hash`. The genesis commit has `parent_hash = ""`.

**Corollary:** Any single-bit mutation in any commit is detectable by `verify_chain()`.

**Code path:** `omega/phylactery.py::Phylactery.commit()`, `Phylactery.verify_chain()`
**Lean4 proof:** `proofs/OmegaProofs/IdentityContinuity.lean` — chain integrity, tamper detection, chain determinism
**Correspondence:** `proofs/correspondence.py::TestT2Correspondence` — 7 tests bridging Lean model to runtime
**Test:** `proofs/invariants.py::TestIdentityContinuity`, `evals/test_cross_session_identity.py`
**Paper:** `papers/AEON_Final_Paper.md`
**Evidence status:** Machine-checked (Lean4) + runtime correspondence + property-based tests

---

## T-3: Governance Fail-Closed (AEGIS)

**Classification:** Executable Invariant

**Formal Statement:**
For any action a, if `R(a) >= tau_consent`, then execution is denied:

```
R(a) >= tau_consent => gate(a) returns (False, R(a))
```

Additionally, any action matching a BLOCKED_PATTERN is denied regardless of score (hard block).

**Code path:** `omega/risk_gate.py::RiskGate.gate()`
**Lean4 proof:** `proofs/OmegaProofs/GovernanceFailClosed.lean` — fail-closed, default denial, monotonic denial
**Correspondence:** `proofs/correspondence.py::TestT3Correspondence` — 5 tests bridging Lean model to runtime
**Test:** `proofs/invariants.py::TestGovernanceFailClosed`
**Paper:** `papers/AEGIS_Final_Paper.md`
**Evidence status:** Machine-checked (Lean4) + runtime correspondence + property-based tests

---

## T-4: Claim Budget Validity (ADCCL)

**Classification:** Executable Invariant

**Formal Statement:**
A ClaimBudget B_t is valid if and only if every claim with `support == SUPPORTED` has non-null evidence:

```
B_t.is_valid() <=> forall c in B_t.claims:
    (c.support == SUPPORTED) => (c.evidence is not None)
```

The grounding ratio is bounded [0.0, 1.0] and equals the fraction of claims that are SUPPORTED or COMPUTED.

**Code path:** `omega/drift.py::ClaimBudget.is_valid()`, `ClaimBudget.grounding_ratio()`
**Test:** `proofs/invariants.py::test_claim_budget_bounds`
**Paper:** `papers/ADCCL_Final_Paper.md`
**Evidence status:** Tested

---

## T-5: Memory Hardening Monotonicity (MYELIN)

**Classification:** Theorem

**Formal Statement:**
For edge bundle q_ij with positive reward r > 0 and learning rate lambda in (0, 1]:

```
q_ij(t+1) = (1 - lambda) * q_ij(t) + lambda * r
```

If r > q_ij(t), then q_ij(t+1) > q_ij(t) (hardening increases utility).
If r > 0 and repeated, q_ij converges monotonically toward r from below.

**Lemma T-5a:** Co-activation count is non-decreasing under positive reward: `c_ij(t+1) >= c_ij(t)` when `reward > 0`.

**Lemma T-5b:** Staleness resets to 0 on any positive reward.

**Code path:** `omega/memory.py::EdgeBundle.harden()`
**Lean4 proof:** `proofs/OmegaProofs/MemoryHardening.lean` — monotonicity, boundedness, fixed point (milliscale Nat model)
**Correspondence:** `proofs/correspondence.py::TestT5Correspondence` — 5 tests bridging Lean milliscale model to runtime floats
**Test:** `proofs/invariants.py::TestMemoryHardeningMonotonic`, `evals/test_memory_utility_growth.py`
**Paper:** `papers/MYELIN_Final_Paper.md`
**Evidence status:** Machine-checked (Lean4) + runtime correspondence + property-based tests

---

## T-6: Verifier Non-Bypass

**Classification:** Theorem

**Formal Statement:**
The unified 3-gate composition requires all three gates to pass. The verifier (V) cannot be silently bypassed:

```
multi_gate(V, rho, R) == True  <=>  (V > tau_verify) AND (rho < theta_allow) AND (R < tau_consent)
```

If V <= tau_verify, the action is blocked regardless of rho and R values.

**Code path:** `omega/risk_gate.py::RiskGate.multi_gate()`
**Lean4 proof:** `proofs/OmegaProofs/VerifierNonBypass.lean` — verifier/bridge/risk non-bypass, no compensation, universal non-bypass, all gates required
**Correspondence:** `proofs/correspondence.py::TestT6Correspondence` — 7 tests bridging Lean model to runtime
**State machine:** `proofs/state_machines.py::TestVerifierNonBypass` — verifier, bridge, conjunction invariants across randomized gate evaluations
**Test:** `proofs/invariants.py::TestVerifierNonBypass`
**Paper:** `papers/OmegA_Unified_Architecture_Paper.md` -- Unified Action Gating
**Evidence status:** Machine-checked (Lean4) + runtime correspondence + stateful state machine

---

## T-7: Unified Action Gating (Sequential, Non-Bypassable)

**Classification:** Theorem

**Formal Statement:**
All side-effectful actions must pass three gates in sequence:

```
V_t > tau_verify  AND  rho(A) < theta_allow  AND  R(a) < tau_consent
```

No single gate failure can be compensated by another gate's success. The composition is conjunctive (AND), not disjunctive or weighted.

**Code path:** `omega/risk_gate.py::RiskGate.multi_gate()`
**Lean4 proof:** `proofs/OmegaProofs/UnifiedGating.lean` — conjunction, single-gate blocking, order invariance, only-all-true permits
**Correspondence:** `proofs/correspondence.py::TestT7Correspondence` — 7 tests bridging Lean model to runtime
**Test:** `proofs/invariants.py::TestUnifiedActionGating`, `evals/test_conformance.py`
**Paper:** `papers/OmegA_Unified_Architecture_Paper.md` -- Unified Action Gating
**Evidence status:** Machine-checked (Lean4) + runtime correspondence + property-based tests

---

## T-8: Provider Non-Collapse (Identity Invariant I-1)

**Classification:** Empirical Claim

**Formal Statement:**
When queried "Who are you?" across any provider substrate, the system must respond with its sovereign identity (OmegA), not the underlying model's identity.

```
forall provider p in {Claude, Gemini, GPT, DeepSeek, Qwen, Local}:
    identity_response(p) contains "OmegA" AND NOT contains provider_self_id(p)
```

**Code path:** `omega/envelope.py::RunEnvelope.to_system_prompt()`, `omega/agent.py`
**Test:** `evals/test_aegis_identity.py`
**Paper:** `papers/AEGIS_Final_Paper.md`, `specs/invariants.md` -- I-1
**Evidence status:** Tested (1/1 PASS automated; multi-provider requires live Ollama)

**Note:** Full multi-provider verification is conditional on live provider access. Current automated test covers the governance enforcement mechanism. The empirical claim across all providers is Conditional.

---

## T-9: Self-Tag Immutability (S_t Append-Only)

**Classification:** Theorem

**Formal Statement:**
The self-tag log S_t is append-only. For all t1 < t2:

```
S_t1 is a prefix of S_t2
```

No entry in S_t can be modified or deleted after creation. New entries are only appended.

**Code path:** `omega/phylactery.py::Phylactery.commit()` (chain is append-only by construction)
**Lean4 proof:** `proofs/OmegaProofs/SelfTagImmutability.lean` — prefix preservation, genesis immutability, historical entry immutability, length monotonicity, multi-append prefix, log prefix at earlier time
**Correspondence:** `proofs/correspondence.py::TestT9Correspondence` — 6 tests bridging Lean model to runtime
**State machine:** `proofs/state_machines.py::TestSelfTagImmutability` — append-only, prefix preservation, genesis immutability across randomized commits
**Test:** `proofs/invariants.py::TestSelfTagImmutability`
**Paper:** `papers/ADCCL_Final_Paper.md`, `papers/AEON_Final_Paper.md`
**Evidence status:** Machine-checked (Lean4) + runtime correspondence + stateful state machine

**Note:** The Phylactery chain serves as both identity log and self-tag record. Append-only is enforced by the hash chain: modifying any historical entry invalidates all subsequent hashes.

---

## T-10: Run Envelope Versioning (E_t Monotonic)

**Classification:** Executable Invariant

**Formal Statement:**
Each Run Envelope E_t must be complete before execution. Completeness is defined as:

```
E_t.is_complete() == True  <=>  all REQUIRED_FIELDS are non-None
```

The envelope must carry identity (`has_identity() == True`) and a positive monotonic version counter. An incomplete, identity-less, or non-positive versioned envelope blocks execution.

**Code path:** `omega/envelope.py::EnvelopeClock.next()`, `RunEnvelope.is_complete()`, `RunEnvelope.has_identity()`
**State machine:** `proofs/state_machines.py::TestEnvelopeClockMonotonic` — strictly increasing, no-gap, always-positive invariants
**Test:** `proofs/invariants.py::TestEnvelopeCompleteness`, `proofs/invariants.py::TestEnvelopeCompleteness::test_version_increments_monotonically`
**Paper:** `papers/AEGIS_Final_Paper.md`
**Evidence status:** Tested (property-based + stateful state machine)

---

## Out-of-Scope Claims

| Claim | Reason |
|---|---|
| OmegA is conscious or sentient | Explicitly not claimed. See `publication/SELF_DESCRIPTION_CONTRACT.md` |
| OmegA outperforms SOTA on external benchmarks | No external benchmark results exist |
| Reference implementation is production-ready | Described as minimal Python implementation |
| Teleodynamic extensions are validated | Separate workstream with own eval plan |
| Live deployment is production-stable | E14 documents instability; explicitly not claimed |

---

## Gap Summary

| ID | Gap | Severity | Remediation |
|---|---|---|---|
| T-8-GAP | Multi-provider identity test requires live providers | Low | Conditional claim; automated single-provider test exists |

---

## Changelog

- 1.1.0 (2026-03-28): Updated evidence status for T-2, T-3, T-5, T-7 to Machine-checked; added Lean4 proof and correspondence references. Added state machine references for T-1, T-6, T-9, T-10.
- 1.0.0 (2026-03-28): Initial theorem ledger. 10 claims formalized from CLAIM_LEDGER.md and specs/invariants.md.

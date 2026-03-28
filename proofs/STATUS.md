# OmegA Proof Status

**Last updated:** 2026-03-28
**Lean4 toolchain:** leanprover/lean4:v4.20.0-rc1

This is the single truth page for the proof surface of OmegA.

## Proof Levels

| Level | Meaning |
|---|---|
| **Machine-checked** | Lean4 formal proof + runtime correspondence tests |
| **Stateful-verified** | Hypothesis stateful state machine (randomized transitions + invariant checks) |
| **Property-tested** | Hypothesis property-based randomized tests |
| **Fuzz-tested** | Hypothesis fuzzing over malformed/boundary inputs |
| **Deterministic** | Fixed assertions in conformance/eval suite |

## Theorem Status

| ID | Theorem | Proof Level | Lean4 | Correspondence | State Machine | Property | Fuzz | Gate |
|---|---|---|---|---|---|---|---|---|
| T-1 | State vector well-formedness | Stateful-verified | -- | -- | Yes (7 invariants) | Yes (6 tests) | -- | Yes |
| T-2 | Identity continuity (hash chain) | Machine-checked | Yes | Yes (7 tests) | -- | Yes (5 tests) | Yes | Yes |
| T-3 | Governance fail-closed | Machine-checked | Yes | Yes (5 tests) | -- | Yes (4 tests) | -- | Yes |
| T-4 | Claim budget validity | Property-tested | -- | -- | -- | Yes (6 tests) | Yes | Yes |
| T-5 | Memory hardening monotonicity | Machine-checked | Yes | Yes (5 tests) | -- | Yes (5 tests) | Yes | Yes |
| T-6 | Verifier non-bypass | Machine-checked | Yes | Yes (7 tests) | Yes (3 invariants) | Yes (2 tests) | -- | Yes |
| T-7 | Unified 3-gate conjunction | Machine-checked | Yes | Yes (7 tests) | -- | Yes (1 test) | -- | Yes |
| T-8 | Provider non-collapse | Conditional | -- | -- | -- | -- | -- | Deferred |
| T-9 | Self-tag immutability | Machine-checked | Yes | Yes (6 tests) | Yes (5 invariants) | Yes (3 tests) | Yes | Yes |
| T-10 | Envelope versioning | Stateful-verified | -- | -- | Yes (3 invariants) | Yes (5 tests) | Yes | Yes |

## Lean4 Proof Files

| File | Theorems | Key Results |
|---|---|---|
| `OmegaProofs/IdentityContinuity.lean` | T-2 | chain integrity, tamper detection, chain determinism |
| `OmegaProofs/GovernanceFailClosed.lean` | T-3 | fail-closed, default denial, monotonic denial |
| `OmegaProofs/MemoryHardening.lean` | T-5 | monotonicity (milliscale), boundedness, fixed point |
| `OmegaProofs/VerifierNonBypass.lean` | T-6 | verifier/bridge/risk non-bypass, no compensation, universal non-bypass |
| `OmegaProofs/UnifiedGating.lean` | T-7 | conjunction, single-gate blocking, order invariance, only-all-true permits |
| `OmegaProofs/SelfTagImmutability.lean` | T-9 | prefix preservation, genesis immutability, entry immutability, monotonic length |

## Test Counts

| Suite | File | Count |
|---|---|---|
| Property-based | `proofs/invariants.py` | 36 tests |
| Correspondence | `proofs/correspondence.py` | 42 tests |
| State machines | `proofs/state_machines.py` | 4 machines |
| Fuzz: envelope | `proofs/fuzz_envelope.py` | varies |
| Fuzz: phylactery | `proofs/fuzz_phylactery.py` | varies |
| Fuzz: memory | `proofs/fuzz_memory.py` | varies |
| Fuzz: drift | `proofs/fuzz_drift.py` | varies |
| Conformance | `evals/test_conformance.py` | 59 assertions |

## Release Gate

`verify.sh` runs all of the following in sequence:

1. Python syntax check
2. Knowledge graph integrity
3. Master evaluation (`omegactl.py eval`)
4. Proof audit (`tools/proof_auditor.py`)
5. Polyglot runtime validation (Rust build+test, MCP build, web build)
6. Formal invariant suite (36/36 property tests, T-1 through T-10)
7. Proof-to-implementation correspondence tests (42/42)
8. State machine tests (4/4)
9. Lean4 machine-checked proofs (6 files, full `lake build`)

## Remaining Work

| Item | Status | Blocker |
|---|---|---|
| T-1 Lean formalization | Not started | Optional — state machine coverage is strong |
| T-4 Lean formalization | Not started | Low priority — property tests sufficient |
| T-8 multi-provider test | Conditional | Requires live Ollama with multiple models |
| T-10 Lean formalization | Not started | Optional — state machine coverage is strong |
| T-5 Mathlib real-number proof | Not started | Requires Mathlib dependency |
| TLA+ model checking | Not started | Requires Java (not installed) |
| Reproducibility container | Not started | Docker/devcontainer |

## Pinnacle Completion Criteria

- [x] All 10 theorem entries mapped in ledger
- [x] Core theorem set machine-checked (T-2, T-3, T-5, T-6, T-7, T-9)
- [x] Runtime correspondence complete for all machine-checked theorems
- [x] Transition theorems covered by state machines (T-1, T-6, T-9, T-10)
- [x] Full release gate green
- [x] Fuzz harnesses for boundary behavior
- [x] Claim auditor in release gate
- [x] No undocumented claims
- [ ] One-command outsider verification script
- [ ] External transcript captured and reproducible
- [ ] Reproducibility container

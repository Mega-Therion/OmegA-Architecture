# OmegA Proof System

**Phase:** 1 (Foundation)
**Created:** 2026-03-28

This directory contains the formal proof infrastructure for the OmegA architecture.

## Structure

```
proofs/
  README.md          -- this file
  invariants.py      -- property-based tests (hypothesis) for core invariants
  PROOF_MAP.md       -- claim-to-evidence traceability matrix
```

## Proof Types

| Type | Method | Location |
|---|---|---|
| Property-based tests | Python hypothesis library | `proofs/invariants.py` |
| Deterministic assertions | pytest assertions | `evals/test_conformance.py` |
| Empirical evidence | Evaluation reports | `evals/*.json` |
| Formal statements | Theorem Ledger | `specs/THEOREM_LEDGER.md` |

## How to Run

```bash
python3 -m pytest proofs/invariants.py -v
```

If hypothesis is not installed:
```bash
pip install hypothesis pytest
```

## Relationship to Other Artifacts

- `specs/THEOREM_LEDGER.md` -- formal statement of every claim, classified by type
- `proofs/PROOF_MAP.md` -- maps each claim through: formal statement -> code -> test -> runtime artifact -> log
- `evals/test_conformance.py` -- 59-assertion conformance suite (deterministic)
- `publication/CLAIM_LEDGER.md` -- human-readable claim status table (predecessor to THEOREM_LEDGER)

## Phase 2 Plan

- Lean4 / Coq formalization of T-2 (hash chain integrity) and T-7 (gate composition)
- Symbolic execution of risk gate score bounds
- Fuzzing harness for envelope completeness
- Monotonic version counter for RunEnvelope (closes T-10-GAP)

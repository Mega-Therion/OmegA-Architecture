# OmegA Proof System

**Phase:** 2 (Machine-Checked Core)
**Created:** 2026-03-28

This directory contains the formal proof infrastructure for the OmegA architecture.

## Structure

```
proofs/
  README.md              -- this file
  invariants.py          -- 36 property-based tests (hypothesis) for all 10 theorems
  correspondence.py      -- 29 proof-to-implementation correspondence tests
  state_machines.py      -- 4 stateful state machine tests (T-1, T-6, T-9, T-10)
  PROOF_MAP.md           -- claim-to-evidence traceability matrix
  lakefile.toml          -- Lean4 Lake project config
  lean-toolchain         -- pinned Lean4 version
  OmegaProofs.lean       -- root import
  OmegaProofs/
    Basic.lean           -- (generated stub)
    IdentityContinuity.lean  -- T-2: Phylactery hash chain (machine-checked)
    MemoryHardening.lean     -- T-5: MYELIN monotonicity (machine-checked)
    UnifiedGating.lean       -- T-7: 3-gate conjunction (machine-checked)
    GovernanceFailClosed.lean -- T-3: AEGIS fail-closed (machine-checked)
tools/proof_auditor.py   -- drift check for theorem/claim/proof correspondence
```

## Proof Types

| Type | Method | Location | Status |
|---|---|---|---|
| Machine-checked proofs | Lean4 | `proofs/OmegaProofs/*.lean` | T-2, T-3, T-5, T-7 |
| Proof-to-impl correspondence | Python hypothesis | `proofs/correspondence.py` | T-2, T-3, T-5, T-7 (29 tests) |
| Stateful state machines | Python hypothesis | `proofs/state_machines.py` | T-1, T-6, T-9, T-10 (4 machines) |
| Property-based tests | Python hypothesis | `proofs/invariants.py` | T-1 through T-10 (36 tests) |
| Deterministic assertions | pytest | `evals/test_conformance.py` | 59 assertions |
| Empirical evidence | Evaluation reports | `evals/*.json` | recorded |
| Formal statements | Theorem Ledger | `specs/THEOREM_LEDGER.md` | 10 theorems |

## How to Run

### Property-based tests (requires Python + hypothesis)
```bash
python3 -m pytest proofs/invariants.py -v
```

### Machine-checked proofs (requires Lean4)
```bash
cd proofs && lake build
```

### Full release gate (runs both)
```bash
bash verify.sh
```

### Install Lean4 (if not present)
```bash
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
```

## Relationship to Other Artifacts

- `specs/THEOREM_LEDGER.md` -- formal statement of every claim, classified by type
- `proofs/PROOF_MAP.md` -- maps each claim through: formal statement -> code -> test -> runtime artifact -> log
- `tools/proof_auditor.py` -- executable drift check that keeps the proof surface synchronized
- `evals/test_conformance.py` -- 59-assertion conformance suite (deterministic)
- `publication/CLAIM_LEDGER.md` -- human-readable claim status table (predecessor to THEOREM_LEDGER)

## What is Machine-Checked

| Theorem | Lean4 Proofs | What is Proven |
|---|---|---|
| T-2 | `IdentityContinuity.lean` | Chain integrity, tamper detection, chain determinism |
| T-3 | `GovernanceFailClosed.lean` | Fail-closed gate, monotonic denial, default denial |
| T-5 | `MemoryHardening.lean` | Monotonicity, boundedness, fixed point |
| T-7 | `UnifiedGating.lean` | Conjunction required, single-gate blocking, order invariance, only-all-true permits |

## Remaining Phase 3 Work

- TLA+ model checking for T-1, T-6, T-9 — requires Java (Python stateful machines provide equivalent coverage)
- Symbolic execution of risk gate score bounds
- Mathlib integration for full real-number T-5 proofs

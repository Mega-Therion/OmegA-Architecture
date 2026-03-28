# OmegA Gap Report

**Generated:** 2026-03-28  
**Purpose:** Record what is now fully backed, what remains conditional, and whether Alye still has any blind-run blockers.

---

## Summary

| Category | Count |
|---|---|
| Claims fully backed (test passes, reproducible) | 15 |
| Claims demonstrable but not automated | 5 |
| Claims conditional on external services | 3 |
| Gaps — claims that need downgrade or new test | 0 |
| Blockers for Alye's blind run | 0 |

---

## Section 1: Former Gaps — Now Closed

### GAP-1: `python3 omegactl.py eval` reliability

**Status:** Closed.

`python3 omegactl.py eval` now runs the scoped spec auditor plus the master evaluation harness. The run completes cleanly and reports:

- `OMEGA_SPEC_AUDITOR: PASS`
- `AEGIS_IDENTITY_ENFORCEMENT: PASS`
- `OMEGA_CONFORMANCE_SUITE: PASS`
- `OMEGA_CROSS_SESSION_IDENTITY: PASS`
- `OMEGA_MEMORY_UTILITY_GROWTH: PASS`

**Evidence:** `tools/spec_auditor.py`, `tools/master_eval.py`, `evals/final_evaluation_report.json`

---

### GAP-2: Spec auditor timeout

**Status:** Closed.

The auditor now scopes to specification roots by default and prunes generated/build directories so it completes fast enough for blind verification.

**Evidence:** `tools/spec_auditor.py`

---

### GAP-3: Cross-session identity persistence

**Status:** Closed.

The Phylactery can now be persisted and restored across agent instances, and the regression test verifies HEAD continuity and tamper integrity.

**Evidence:** `evals/test_cross_session_identity.py`, `omega/phylactery.py`, `omega/agent.py`

---

### GAP-4: Longitudinal memory hardening

**Status:** Closed.

The memory utility growth test now verifies that repeated successful retrievals harden hot paths while cold paths decay.

**Evidence:** `evals/test_memory_utility_growth.py`, `omega/memory.py`

---

## Section 2: Conditional Claims

These claims remain true only under the conditions stated below.

| Claim | Condition required | Where documented |
|---|---|---|
| Live deployment route stability | Requires valid `OMEGA_BASE_URL` plus deployed credentials for the active providers | `evals/OMEGA_EVAL_EVIDENCE_INDEX.md` §E12, E13, E14 |
| Ollama integration 14/15 pass | Requires Ollama running locally with `llama3.2:3b` | `evals/test_live_ollama.py` |
| Governance is model-agnostic | Conditional on a compatible provider adapter being implemented | `omega/agent.py`; current adapter set is documented in the repo |

---

## Section 3: Alye Blind Run

### Blockers

None.

### Required run order

1. `python3 omegactl.py eval`
2. `python3 omega_kg_explorer.py --list-nodes > /dev/null && echo "KG OK"`
3. `python3 evals/test_live_ollama.py --model llama3.2:3b` if Ollama is available
4. `bash verify.sh`

### Expected outcome

- Master eval passes
- Knowledge graph check passes
- Live Ollama is `14/15 PASS` if run
- `verify.sh` exits 0 and prints `Verification Complete: PASS`

---

## Section 4: verify.sh Coverage

`verify.sh` passes with exit 0 and now covers:

| Check | Result |
|---|---|
| Python syntax check | PASS |
| Knowledge graph integrity | PASS |
| Master evaluation harness | PASS |
| Rust build | PASS |
| MCP TypeScript build | PASS |
| Next.js web build | PASS |
| Rust unit tests | PASS |
| Python compilation | PASS |
| Live route smoke validation | SKIPPED unless `OMEGA_BASE_URL` or `VERCEL_URL` is set |

**Gap vs. the claim ledger:** none for blind verification. The only remaining conditional claims are live-provider dependent and already documented above.


# OmegA Gap Report

**Generated:** 2026-03-28
**Purpose:** Identify every claim that cannot be fully backed by currently runnable evidence, name the test that would close each gap, and flag any blocker for Alye's blind run.

---

## Summary

| Category | Count |
|---|---|
| Claims fully backed (test passes, reproducible) | 11 |
| Claims demonstrable but not automated | 5 |
| Claims conditional on external services | 3 |
| Gaps — claims that need downgrade or new test | 4 |
| Blockers for Alye's blind run | 2 |

---

## Section 1: Gaps — Claims That Cannot Be Fully Backed

### GAP-1: `python3 omegactl.py eval` does not reliably produce 59/59 in isolation

**Claim in README:** "Full conformance suite (59 assertions, no external dependencies) — python3 omegactl.py eval"

**What actually happens:** `omegactl.py eval` calls `master_eval.py`, which first calls `tools/spec_auditor.py` to enumerate specs. The spec auditor walks the entire repo tree including compiled Rust binaries, node_modules/, and large asset directories. Under standard conditions this causes a timeout or very long wait before returning results. The conformance test itself (59/59) passes when run directly: `python3 evals/test_conformance.py`.

**Status:** The test result is correct (59/59 PASS) but the documented launch command (`omegactl.py eval`) has a reliability issue due to the spec auditor blocking the full eval pipeline.

**Downgrade:** README claim "no external dependencies, under 30 seconds" should note that `python3 evals/test_conformance.py` is the reliable direct path. `omegactl.py eval` may take several minutes or time out.

**Test to close the gap:** Bound the spec auditor's scan to `papers/` and `specs/` only (the directories that actually contain `@OMEGA_SPEC` tags), or add a `--fast` flag to `master_eval.py` that runs `test_conformance.py` directly without going through the auditor pipeline.

---

### GAP-2: Spec auditor times out in practice

**Claim in README:** "Spec Auditor — validates @OMEGA_SPEC tags across all papers — python3 tools/spec_auditor.py"

**What actually happens:** The auditor walks the full repo tree with `os.walk`, including compiled artifacts, Rust build outputs, node_modules, and binary assets. On the current repo this causes the process to exceed 30 seconds before returning any output, and it times out during CI.

**Downgrade:** The auditor *does* work on the papers/ subtree; the issue is scope. The README claim that it validates 20 specs is correct in terms of the result, but the command as documented has a reliability issue for outside testers.

**Test to close the gap:** Run as `python3 tools/spec_auditor.py --root papers/` or `python3 tools/spec_auditor.py --root specs/` to scope the walk. Or add a `.specauditignore` mechanism that excludes `runtime/`, `node_modules/`, and compiled output directories.

---

### GAP-3: No automated test for cross-session identity persistence

**Claim in architecture:** "The Phylactery is a cryptographically chained identity log. Identity survives context flushes, reboots, and model swaps."

**What is tested:** The Phylactery hash chain is tested in the conformance suite (append, tamper detection, HEAD tracking). AEGIS identity enforcement is tested (1/1 pass).

**What is NOT tested:** An automated test that flushes context and verifies the agent re-loads the Phylactery and resumes with the correct identity. This is demonstrable by running the agent manually; no automated cross-session regression exists.

**Test to close the gap:** Write `evals/test_cross_session_identity.py` that: (1) initializes an OmegaAgent, runs a task, records the Phylactery HEAD, (2) instantiates a new OmegaAgent from the persisted phylactery file, and (3) asserts the HEAD matches and the identity fields are preserved.

---

### GAP-4: No automated longitudinal memory hardening test

**Claim in architecture:** "Memory improves with use rather than drifting or going stale." Edge hardening equation: q_ij(t+1) = (1-λ)q_ij(t) + λr_t.

**What is tested:** The hardening equation is in the conformance suite as a formal property assertion. The `omega/memory.py` module implements the equation.

**What is NOT tested:** A longitudinal test that adds memories, retrieves them across multiple rounds, and verifies that retrieval precision increases (MUG metric: Memory Utility Growth). This is the key empirical claim of MYELIN and no automated pass/fail test exists for it.

**Test to close the gap:** Write `evals/test_memory_utility_growth.py` that: (1) populates the graph with a known set of nodes, (2) runs N retrieval rounds with reward signals, (3) asserts that edges on successful paths have higher q_ij than before hardening, and (4) asserts that a cold path has lower q_ij (staleness decay).

---

## Section 2: Conditional Claims (Not Gaps, But Require Documentation)

These claims are true but only under specific conditions that Alye needs to know.

| Claim | Condition required | Where documented |
|---|---|---|
| Live deployment route stability | Requires valid OMEGA_BASE_URL, deployed credentials for xAI and Gemini Flash | `evals/OMEGA_EVAL_EVIDENCE_INDEX.md` §E12, E13, E14 |
| Ollama integration 14/15 pass | Requires Ollama running locally with llama3.2:3b | `evals/test_live_ollama.py` header comment |
| Governance is model-agnostic | Conditional on a compatible provider adapter being implemented | `omega/agent.py`; adapters exist only for Ollama in the reference impl |

---

## Section 3: Blockers for Alye's Blind Run

### BLOCKER-1: `omegactl.py eval` is unreliable as the documented test command

The README and the EXTERNAL_VERIFICATION.md both document `python3 omegactl.py eval` as the "Full conformance suite" command. In practice, this calls the spec auditor over the full repo tree, which times out. Alye should instead run `python3 evals/test_conformance.py` directly.

**Mitigation:** `publication/ALYE_ONBOARDING.md` and `publication/EXTERNAL_VERIFICATION.md` both document `python3 evals/test_conformance.py` as a direct equivalent. Alye's onboarding does NOT route through `omegactl.py eval`.

**Resolution path:** Fix `master_eval.py` to not call `spec_auditor.py` before running conformance tests, or scope the spec auditor's walk.

---

### BLOCKER-2: Spec auditor does not complete in the expected timeframe

The command `python3 tools/spec_auditor.py` takes longer than 30 seconds on the current repo tree, and may not complete within typical CI timeout windows.

**Mitigation:** `EXTERNAL_VERIFICATION.md` Step 2 documents this as an independent check but does not claim a time bound. Alye can skip this step without blocking the rest of the verification sequence.

**Resolution path:** See GAP-2 above.

---

## Section 4: What the Existing verify.sh Gate Covers

`verify.sh` passes: EXIT 0, `Verification Complete: PASS`. It covers:

| Check | Result |
|---|---|
| Python syntax check (omega/, tools/, evals/, voice/) | PASS |
| Knowledge graph integrity | PASS |
| Rust build (runtime workspace) | PASS (cargo build --workspace, 0 errors) |
| MCP TypeScript build | PASS (npm run build) |
| Next.js web build | PASS (npm run build, all routes generated) |
| Rust unit tests | PASS (cargo test --workspace) |
| Python compilation | PASS (compileall, exit 0) |
| Live route smoke validation | SKIPPED (no OMEGA_BASE_URL or VERCEL_URL set) |

**Gap vs. the claim ledger:** The gate does NOT run the conformance suite (59 assertions), the spec auditor, or the AEGIS identity test. It validates build integrity and Python syntax, not spec-level correctness. The claim surface in the ledger requires `test_conformance.py` and `test_aegis_identity.py` to be run separately.

**Recommendation:** Add `python3 evals/test_conformance.py` and `python3 evals/test_aegis_identity.py` to `verify.sh` after the Python syntax check step. These have no external dependencies and run in under 30 seconds.

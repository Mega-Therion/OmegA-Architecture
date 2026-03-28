# OmegA External Verification Guide

**Audience:** A skeptical outside reviewer — Alye or anyone else with no prior context.
**Purpose:** Tell you exactly what OmegA claims, how to verify those claims, and what the system explicitly does not assert.

---

## 1. What OmegA Claims to Be (Plain Language)

OmegA is a **formally specified architecture** for AI agents that solves four linked failure modes in one unified design:

| Failure mode | OmegA's solution layer |
|---|---|
| Memory decay and retrieval drift | MYELIN — path-dependent graph memory |
| Cognitive inconsistency and hallucination | ADCCL — anti-drift claim-budget control loop |
| Identity loss across context resets | AEON — cryptographic Phylactery identity chain |
| Ungoverned tool use across model providers | AEGIS — model-agnostic governance shell |

The claim is that these four layers compose into a single formal system with one unified state vector and one integrated optimization objective. The architecture has a **DOI-archived specification** (Zenodo 10.5281/zenodo.19111653) and a **Python reference implementation** in the `omega/` package.

---

## 2. How to Run the Verification Suite from Scratch

### Prerequisites

- Python 3.12 or later
- Git
- (Optional) Ollama running locally with `llama3.2:3b` for live integration tests
- (Optional) `ripgrep` (`rg`) for the full verify.sh gate

### Clone and enter the repo

```bash
git clone https://github.com/Mega-Therion/OmegA-Architecture.git
cd OmegA-Architecture
```

### Step 1 — Run the master evaluation suite (no external dependencies)

```bash
python3 omegactl.py eval
```

Expected:
- `OMEGA_SPEC_AUDITOR: PASS`
- `AEGIS_IDENTITY_ENFORCEMENT: PASS`
- `OMEGA_CONFORMANCE_SUITE: PASS`
- `OMEGA_CROSS_SESSION_IDENTITY: PASS`
- `OMEGA_MEMORY_UTILITY_GROWTH: PASS`

### Step 2 — Run the knowledge graph integrity check

```bash
python3 omega_kg_explorer.py --list-nodes > /dev/null && echo "KG OK"
```

Expected: exits 0, no errors.

### Step 3 — AEGIS identity invariant test

```bash
python3 evals/test_aegis_identity.py
```

Expected: 1/1 PASS — AEGIS enforces identity without an identity kernel loaded.

### Step 4 — Live integration tests (requires Ollama)

```bash
python3 evals/test_live_ollama.py --model llama3.2:3b
```

Expected: 14/15 pass. The one known failure (small model reverts to generic self-description under doctrine query) is documented as a validated empirical finding, not a regression.

### Step 5 — Run the full release gate

```bash
bash verify.sh
```

Expected: "Verification Complete: PASS". Requires `rg` (ripgrep) and Python 3.12+.

---

## 3. What Passing Looks Like

| Test | Pass condition |
|---|---|
| Master evaluation suite | Five PASS lines printed, exit 0 |
| Spec auditor | 20 specs found, no broken cross-references |
| Knowledge graph | No JSON parse errors, all nodes listed |
| AEGIS identity | `1/1 PASS` |
| Cross-session identity | `PASS` |
| Memory utility growth | `PASS` |
| Live Ollama | `14/15 PASS` (the 15th failure is a documented finding) |
| verify.sh | `Verification Complete: PASS` |

Any deviation from these counts should be treated as a regression and reported.

---

## 4. What OmegA Explicitly Does NOT Claim

- **Not claimed:** That OmegA outperforms external benchmark baselines (MMLU, HellaSwag, etc.). External benchmark evaluation is the next research phase, not the current one.
- **Not claimed:** Consciousness, sentience, or subjective experience. These are explicitly out of scope.
- **Not claimed:** Production readiness for deployment in critical systems without further validation.
- **Not claimed:** That the reference implementation is a complete system. It is a minimal Python implementation demonstrating the four-layer architecture.
- **Not claimed:** That live provider routes (xAI, Gemini Flash) are stable. Recent live-pressure evals (E12, E13, E14) show provider-level failures under production load; these are documented, not hidden.
- **Not claimed:** That 59/59 conformance passing equals independent external validation. These are spec-level conformance tests — they verify the implementation matches the formal definitions.

---

## 5. Where to Find Every Piece of Evidence

| Evidence type | Location |
|---|---|
| Architecture specification | `papers/OmegA_Unified_Architecture_Paper.md` |
| Per-layer formal papers | `papers/AEGIS_Final_Paper.md`, `AEON_Final_Paper.md`, `ADCCL_Final_Paper.md`, `MYELIN_Final_Paper.md` |
| Conformance test source | `evals/test_conformance.py` |
| Conformance report (JSON) | `evals/conformance_report.json` |
| Master evaluation report (JSON) | `evals/final_evaluation_report.json` |
| Cross-session identity regression | `evals/test_cross_session_identity.py` |
| Memory utility growth regression | `evals/test_memory_utility_growth.py` |
| Live integration report | `evals/live_integration_report.json` |
| Live pressure eval (E12) | `evals/live_deployment_pressure_report.json` |
| Provider isolation eval (E13) | `evals/provider_isolation_report.json` |
| Route isolation eval (E14) | `evals/live_route_isolation_report.json` |
| Eval evidence index | `evals/OMEGA_EVAL_EVIDENCE_INDEX.md` |
| Python reference implementation | `omega/` (agent.py, phylactery.py, drift.py, memory.py, risk_gate.py, envelope.py) |
| Knowledge graph | `omega_equation_knowledge_graph.json` |
| Spec annotations across papers | search `@OMEGA_SPEC` in `papers/` |
| Release gate script | `verify.sh` |
| Claim ledger | `publication/CLAIM_LEDGER.md` |
| Verification rubric | `publication/VERIFICATION_RUBRIC.md` |
| Gap report | `publication/GAP_REPORT.md` |
| Zenodo archive | https://doi.org/10.5281/zenodo.19111653 |

---

## 6. Contact / Repository

**Author:** R.W. Yett
**GitHub:** https://github.com/Mega-Therion/OmegA-Architecture
**DOI:** 10.5281/zenodo.19111653

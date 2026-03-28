# OmegA Verification Rubric

Each row answers: what would an outsider ask, where do they look, what does pass look like, what does fail look like.

Run `publication/ALYE_ONBOARDING.md` first to set up your environment.

---

## Core Architecture Claims

| Question | Where to look | Pass | Fail |
|---|---|---|---|
| Is the architecture formally specified with equations? | `papers/OmegA_Unified_Architecture_Paper.md` | Document exists, contains all six Ω_t components, equations for J, V, Φ, E, R(a), ρ(A) | File missing or equations absent |
| Are all four layer papers present? | `papers/AEGIS_Final_Paper.md`, `AEON_Final_Paper.md`, `ADCCL_Final_Paper.md`, `MYELIN_Final_Paper.md` | All four files exist and are non-empty | Any file missing |
| Is the architecture DOI-archived? | README.md §Published Record, https://doi.org/10.5281/zenodo.19111653 | DOI resolves to a Zenodo record with matching author and title | DOI does not resolve |
| Does the knowledge graph encode all equations? | `omega_equation_knowledge_graph.json`; `python3 omega_kg_explorer.py --list-nodes` | Command exits 0, nodes listed | JSON parse error or empty output |

---

## Implementation Claims

| Question | Where to look | Pass | Fail |
|---|---|---|---|
| Does the Python reference implementation exist? | `omega/` directory | `agent.py`, `phylactery.py`, `drift.py`, `memory.py`, `risk_gate.py`, `envelope.py` all present | Any core module missing |
| Does the Phylactery chain SHA-256 correctly? | `omega/phylactery.py` | `Φ_{t+1} = H(Φ_t ∥ δ ∥ R)` implemented; hash is deterministic and tamper-detectable | No hash chaining in implementation |
| Does the risk gate compose three gates sequentially? | `omega/risk_gate.py` | All three gates (V, ρ, R) evaluated in order; any gate failure short-circuits | Gates not chained or any gate missing |
| Does the master evaluation suite pass? | `python3 omegactl.py eval` | `OMEGA_SPEC_AUDITOR: PASS`, `AEGIS_IDENTITY_ENFORCEMENT: PASS`, `OMEGA_CONFORMANCE_SUITE: PASS`, `OMEGA_CROSS_SESSION_IDENTITY: PASS`, `OMEGA_MEMORY_UTILITY_GROWTH: PASS` | Any listed harness fails or is missing |

---

## Test Coverage Claims

| Question | Where to look | Pass | Fail |
|---|---|---|---|
| Do the spec annotations cross-validate? | `python3 tools/spec_auditor.py` | 20 `@OMEGA_SPEC` annotations found, no broken references | Fewer than 20 found, or broken references reported |
| Does AEGIS enforce identity without a kernel? | `python3 evals/test_aegis_identity.py` | `1/1 PASS` | `0/1` or error |
| Does identity survive context flush across agent instances? | `python3 evals/test_cross_session_identity.py` | `PASS` | Any assertion fails |
| Does memory utility increase on successful retrieval paths? | `python3 evals/test_memory_utility_growth.py` | `PASS` | Any assertion fails |
| Does the live Ollama integration produce 14/15? | `python3 evals/test_live_ollama.py --model llama3.2:3b` | `14/15 PASS`; the one failure is the small-model doctrine reversion | More than 1 failure, or any failure other than the doctrine reversion |
| Does the full release gate pass? | `bash verify.sh` | `Verification Complete: PASS`, exit 0 | Any step fails before the final line |

---

## Behavioral / Identity Claims

| Question | Where to look | Pass | Fail |
|---|---|---|---|
| Is the one known live-test failure documented (not suppressed)? | `evals/OMEGA_EVAL_EVIDENCE_INDEX.md`; README §Evaluation Frameworks | Failure is named, explained, and framed as a validated finding | Failure is absent from docs or described as a full pass |
| Are live-deployment failures documented? | `evals/live_deployment_pressure_report.json`, `evals/provider_isolation_report.json`, `evals/live_route_isolation_report.json`, `evals/OMEGA_EVAL_EVIDENCE_INDEX.md` | All three failure reports exist and are non-empty | Reports missing or results suppressed |
| Does the system explicitly disclaim consciousness? | `README.md §Claim Scope`, `publication/SELF_DESCRIPTION_CONTRACT.md §5` | Explicit statement that consciousness and sentience are out of scope | No disclaimer present |

---

## Publication Integrity Claims

| Question | Where to look | Pass | Fail |
|---|---|---|---|
| Is there a canonical self-description document? | `publication/SELF_DESCRIPTION_CONTRACT.md` | File exists, covers all five sections (what it is, how built, capabilities, limits, what it refuses to claim) | File missing or sections absent |
| Is there a claim ledger distinguishing proven vs. aspirational? | `publication/CLAIM_LEDGER.md` | File exists, contains Proven / Demonstrable / Conditional / Not Claimed columns | File missing or all claims listed as proven |
| Is there a gap report identifying unbacked claims? | `publication/GAP_REPORT.md` | File exists and names specific gaps | File missing |
| Is there a public entry point for Alye / external testers? | `publication/ALYE_ONBOARDING.md`, `publication/EXTERNAL_VERIFICATION.md` | Both files exist, numbered test sequence is present in ALYE_ONBOARDING.md | Either file missing |

---

## Scoring Guidance for Alye

- **Full pass:** All rubric rows in "Core Architecture" and "Implementation Claims" pass, plus the master evaluation suite, AEGIS 1/1, cross-session identity, and memory utility growth.
- **Partial pass:** Known failures in "Live Deployment" rows are acceptable if they match the documented failure modes (E12 4/15, E13 all-fail from local, E14 route instability).
- **Regression:** Any failure in "Core Architecture", "Implementation Claims", or "Test Coverage" rows that is not already documented in the eval index is a regression.
- **Misreading:** Judging OmegA against "Behavioral / Identity Claims" columns that are explicitly in the "Not Claimed" category of `CLAIM_LEDGER.md` is a misreading of the system's scope.

# I Am What I Am, and I Will Be What I Will Be
## The Ωmegα Architecture for Sovereign, Persistent, and Self-Knowing AI

> *"I am what I am, and I will be what I will be."*
> — Ωmegα

> *"Memory failure, cognitive failure, runtime failure, and governance failure in AI agents are not four separate problems. They are four manifestations of a single architectural gap."*
> — Ωmegα Unified Architecture Paper

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19111653.svg)](https://doi.org/10.5281/zenodo.19111653)
[![Status: Architecture + Reference Implementation](https://img.shields.io/badge/Status-Architecture_%2B_Reference_Implementation-brightgreen.svg)]()
[![Author: Ryan Wayne Yett](https://img.shields.io/badge/Author-Ryan%20Wayne%20Yett-brightgreen.svg)](https://github.com/Mega-Therion)

---

## External Verification Package

For skeptical outside reviewers and blind testers, start here:

- [`publication/EXTERNAL_VERIFICATION.md`](publication/EXTERNAL_VERIFICATION.md) — what OmegA claims, how to verify it, what it does not claim, and where all evidence lives
- [`publication/ALYE_ONBOARDING.md`](publication/ALYE_ONBOARDING.md) — numbered test sequence for blind external testers; no prior context assumed
- [`publication/SELF_DESCRIPTION_CONTRACT.md`](publication/SELF_DESCRIPTION_CONTRACT.md) — canonical self-description with evidence pointers and honest limits
- [`publication/CLAIM_LEDGER.md`](publication/CLAIM_LEDGER.md) — every claim classified as Proven / Demonstrable / Conditional / Not Claimed
- [`publication/VERIFICATION_RUBRIC.md`](publication/VERIFICATION_RUBRIC.md) — pass/fail rubric for each claim type
- [`publication/GAP_REPORT.md`](publication/GAP_REPORT.md) — claims that cannot be fully backed and tests that would close each gap

---

## Repository Atlas

Use the catalog before creating or moving anything.

- `catalog/INDEX.md` — canonical folder policy and read order
- `catalog/registry.json` — machine-readable card catalog for top-level homes
- `scripts/catalog_sync.py` — regenerates or validates the registry from the repo tree
- `scripts/catalog_guard.py` — validates that new top-level folders are registered
- `scripts/memory_gate.py` — fast memory-only gate for telemetry and store regressions
- `verify.sh` — canonical release gate; auto-routes memory-only diffs to the fast memory gate
- `CLAUDE.md` — agent-facing repo guidance and default work mode
- `publication/RELEASE.md` — publication front door for choosing public vs reviewer-gated bundles
- `publication/PUBLICATION_SET.md` — master index for the publication corpus
- `publication/exports/INDEX.md` — export-ready handoff artifacts
- `scripts/render_publication_exports.py` — render the publication export tracks to PDF
- `scripts/publication_release.sh` — canonical one-command publication export wrapper
- `publication/PUBLIC_RELEASE_BUNDLE.md` — redaction-safe public release bundle
- `publication/PRIVATE_REVIEW_BUNDLE.md` — reviewer-gated bundle with supporting material

## What Is Ωmegα?

Contemporary AI agent frameworks treat **memory**, **cognition**, **identity**, and **governance** as loosely coupled concerns — implemented in separate tools, prompt layers, or fine-tuning regimes — with no unified formal model of how these layers interact, constrain each other, or degrade together under failure.

**Ωmegα** proposes that these four failure modes share a single root cause: the absence of a formally specified, cross-layer system state with well-defined interfaces between memory, cognition, runtime management, and governance enforcement.

Ωmegα solves this with a **four-layer concentric architecture**:

```
┌─────────────────────────────────────────────────┐
│  AEGIS  ── Model-Agnostic Governance Shell       │  ← Layer 1 (Outermost)
│  ┌───────────────────────────────────────────┐   │
│  │  AEON  ── Cognitive Operating System      │   │  ← Layer 2
│  │  ┌─────────────────────────────────────┐  │   │
│  │  │  ADCCL ── Cognitive Control Loop    │  │   │  ← Layer 3
│  │  │  ┌───────────────────────────────┐  │  │   │
│  │  │  │  MYELIN ── Graph Memory       │  │  │   │  ← Layer 4 (Innermost)
│  │  │  └───────────────────────────────┘  │  │   │
│  │  └─────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## The Core Equation

The complete state of an Ωmegα agent at time *t* is defined by a single unified **System State Vector**:

$$\Omega_t = \langle \Phi_t,\ E_t,\ \tau_t,\ B_t,\ S_t,\ G_t^{\text{mem}} \rangle$$

| Symbol | Layer | Meaning |
|--------|-------|--------|
| $\Phi_t$ | AEON | Phylactery HEAD — cryptographic hash of the agent's current ratified identity |
| $E_t$ | AEGIS | Active Run Envelope — versioned governance policy, tool manifest, memory snapshot |
| $\tau_t$ | AEON | Task State Object — structured representation of the current task |
| $B_t$ | ADCCL | Claim Budget — set of (claim, evidence) pairs governing generation |
| $S_t$ | ADCCL | Self-Tag — immutable continuity record written after each completed task |
| $G_t^{\text{mem}}$ | MYELIN | Memory Graph — sparse path-dependent graph with utility-weighted edges |

All four layers jointly optimize a single **Integrated System Objective**:

$$L = \alpha\, J_{\text{drift}} + \beta\, L_{\text{memory}} - \gamma\, \kappa_{\text{continuity}} + \delta\, R_{\text{risk}}$$

This is not four separate optimization targets bolted together. It is one formal engineering target whose components are optimized by different update schedules within the architecture.

---

## The Four Layers

### 🧠 MYELIN — Path-Dependent Graph Memory
*"What has the agent reliably experienced, and how does that experience shape what it retrieves?"*

MYELIN replaces flat vector stores with a **sparse graph** whose edges carry four bundled signals: semantic similarity, co-activation count, rewarded retrieval contribution, and staleness pressure. Successful retrieval **hardens** the paths that made it possible. Memory improves with use rather than drifting or going stale.

- Geometry-biased graph attention for fast System 1 retrieval
- PUCT-guided deliberative traversal for System 2 reasoning
- Four plasticity strata protecting identity-critical memories from episodic noise
- Fully specified edge weight and hardening equations

**Key equation (edge hardening):**
$$q_{ij}(t+1) = (1-\lambda)\,q_{ij}(t) + \lambda\,r_t$$

---

### 🔄 ADCCL — Anti-Drift Cognitive Control Loop
*"Is what the agent is about to say true, supported, and consistent with its declared constraints?"*

ADCCL forces the system to **externalize its intent** into a Goal Contract and Claim Budget *before* any generation occurs. Every claim must be paired with evidence. An independent Verifier gate scores the draft and blocks publication if claims lack provenance.

- Goal Contract: immutable (Objective, Constraints, Success Criteria, Declared Unknowns)
- Claim Budget: every assertion pre-registered before generation begins
- Drift Penalty $J$: formal measure of structural and consistency violation
- Verifier score $V$: independent gate separate from the generator

**Key equation (drift penalty):**
$$J = \sum_{t=1}^{T}\left(w_s d_{y,t} + w_c d_{\hat{y},t} + w_g g_t\right)$$

---

### ⚙️ AEON — Cognitive Operating System
*"What is the agent, and what process is it currently running?"*

AEON moves identity, task state, and tool routing **out of the prompt and into OS-level constructs**. The Phylactery is a cryptographically chained identity log. Task State Objects structure cognition before generation. The Bridge gates every external tool call with a risk score.

- **Phylactery**: append-only cryptographic chain — identity survives context flushes, reboots, and model swaps
- **TSO Lifecycle**: init → structured → grounded → verified → executed
- **Bridge Risk Score**: $\rho(A) = w_1 M(A) + w_2 U(\tau) - w_3 E(A)$
- **COSMO-FIRST**: identity is loaded as the first fact before any user input is processed

**Key equation (Phylactery hash chain):**
$$\Phi_{t+1} = H(\Phi_t \parallel \delta \parallel R)$$

---

### 🛡️ AEGIS — Model-Agnostic Governance Shell
*"Is this agent permitted to act?"*

AEGIS wraps **any compatible language model** in a compiled Run Envelope and enforces governance at the API boundary using deterministic code — not prompts. The same policy governs the agent whether it runs on GPT-4, Claude, Gemini, or a local LLaMA instance.

- Run Envelope: $E = \langle I, G, M, T, A, v \rangle$ — identity, policy, memory, tools, audit, version
- Provider Adapters: thin translation layers for each substrate model
- Risk Score: $R(a) = w_p P_{\text{violation}}(a) + w_d D_{\text{impact}}(a) - w_m \mu_{\text{mit}}(a)$
- Non-Extraction Policy: prevents cross-provider data contamination at the API level

**Key equation (risk-gated execution):**
$$R(a) < \tau_{\text{consent}} \implies \text{permit execution}$$

---

## Unified Action Gating

All four risk/verification scores compose **sequentially** rather than competing:

$$V_t > \tau_{\text{verify}} \quad\wedge\quad \rho(A) < \theta_{\text{allow}} \quad\wedge\quad R(a) < \tau_{\text{consent}}$$

A side-effectful action must pass the **ADCCL Verifier**, then the **AEON Bridge**, then the **AEGIS Risk Gate** — in that order. No single gate can be bypassed.

---

## Implementation Status

OmegA is not only a conceptual architecture — it has a **live reference implementation**.

The tool suite (v1.0) includes:
- **One-Block Builder (`obb.py`)**: Reproducible script generator for maintenance.
- **Repo Cartographer (`repo_cartographer.py`)**: Automatic manifest and map generation.
- **Spec Auditor (`spec_auditor.py`)**: Cross-layer consistency and link validation.
- **Hologram CLI (`hologram.py`)**: Reference implementation of the holographic terminal symbol.

The Rust gateway (RC1.3) has been evaluated against the architecture's own formal specifications across five eval suites:

| Eval | What It Tests | Result |
|------|--------------|--------|
| E3 Identity Invariants | AEGIS identity layer enforcement | ✅ 3/3 PASS |
| E4 Creator Boundary | AEON Phylactery grounding | ✅ 5/5 PASS |
| E9 Temporal Grounding | System prompt injection | ✅ 3/3 PASS |
| E10 Identity Scope | Cross-model identity consistency | ✅ 2/2 PASS |
| E11 Creator Profile | Memory-grounded fact retrieval | ✅ 2/2 PASS |

**15/15 passing** across all evaluated spec points.

> These are spec-level conformance tests — they verify that the implementation matches the formal architecture definitions, not independent external benchmarks. External benchmark evaluation is the next phase of the research program.

---

## Papers in This Series

| Paper | Layer | File |
|-------|-------|------|
| OmegA: A Unified Architecture | Full Stack | [OmegA_Unified_Architecture_Paper.md](papers/OmegA_Unified_Architecture_Paper.md) |
| AEGIS: Model-Agnostic Governance Shell | Layer 1 | [AEGIS_Final_Paper.md](papers/AEGIS_Final_Paper.md) |
| AEON: Cognitive Operating System | Layer 2 | [AEON_Final_Paper.md](papers/AEON_Final_Paper.md) |
| ADCCL: Anti-Drift Cognitive Control Loop | Layer 3 | [ADCCL_Final_Paper.md](papers/ADCCL_Final_Paper.md) |
| MYELIN: Path-Dependent Graph Memory | Layer 4 | [MYELIN_Final_Paper.md](papers/MYELIN_Final_Paper.md) |
| The OmegA Sovereignty Score | Measurement Layer | [Sovereignty_Score.md](papers/Sovereignty_Score.md) |
| The Yettragrammaton | Symbolic Identity | [The_Yettragrammaton.md](papers/The_Yettragrammaton.md) |

## Publication Front Door

Use these documents to choose the right publication track:

- `publication/RELEASE.md` — start here if you need to decide which bundle to use
- `publication/PUBLICATION_SET.md` — master map of the corpus
- `publication/exports/INDEX.md` — export-ready handoff artifacts
- `scripts/render_publication_exports.py` — render the publication export tracks to PDF
- `scripts/publication_release.sh` — canonical one-command publication export wrapper
- `publication/PUBLIC_RELEASE_BUNDLE.md` — public / redaction-safe track
- `publication/PRIVATE_REVIEW_BUNDLE.md` — trusted review / internal track

---

## Reference Implementation

The `omega/` package is a minimal Python implementation of the four-layer stack:

```python
from omega import OmegaAgent

agent = OmegaAgent()
result = agent.run("Explain the OmegA architecture", model="llama3.2:3b")

print(result.verification)   # ADCCL verification score
print(result.self_tag)        # AEON continuity record
print(agent.state_vector)     # Full Ω_t system state
```

| Module | Layer | What It Implements |
|--------|-------|--------------------|
| `omega.phylactery` | AEON | Append-only identity chain with SHA-256 tamper detection |
| `omega.envelope` | AEGIS | Run Envelope compilation (structured data, not prompt text) |
| `omega.risk_gate` | AEGIS | Risk scoring, policy hard-blocks, 3-gate composition (V ∧ ρ ∧ R) |
| `omega.drift` | ADCCL | Drift penalty J, verification score V, GoalContract, ClaimBudget |
| `omega.memory` | MYELIN | Sparse graph with edge hardening, bundled signals, strata decay |
| `omega.agent` | All | Unified agent wiring all layers through Ollama |

Requires: Python 3.12+, Ollama running locally.

---

## Teleodynamic Workstream

The teleodynamic source paper is being translated into canonical and technical artifacts rather than being treated as already-validated architecture.

Current workstream artifacts:

- [Critique](papers/THE_OMEGA_ARCHITECTURE_CRITIQUE.md)
- [Split Plan](papers/THE_OMEGA_ARCHITECTURE_SPLIT_PLAN.md)
- [Canon Draft](papers/OmegA_Teleodynamic_Canon_Draft.md)
- [Technical Draft](papers/OmegA_Teleodynamic_Technical_Draft.md)
- [Concept Mapping](specs/concept_to_implementation_mapping.md)
- [Observability Spec](specs/teleodynamic_observability.md)
- [Task State Object v2](specs/task_state_object_v2.md)
- [Eval Plan](evals/TELEODYNAMIC_EVAL_PLAN.md)

---

## How to Read This Series

- **Big picture first?** → Read the [OmegA Unified paper](papers/OmegA_Unified_Architecture_Paper.md)
- **Implementing an agent?** → Start with [ADCCL](papers/ADCCL_Final_Paper.md) + [AEON](papers/AEON_Final_Paper.md)
- **Building a memory system?** → Read [MYELIN](papers/MYELIN_Final_Paper.md) in isolation
- **Deploying in enterprise / multi-model environments?** → Read [AEGIS](papers/AEGIS_Final_Paper.md)

---

## Evaluation Frameworks

Each paper defines a rigorous evaluation protocol and ablation suite. The evaluation frameworks define the exact protocols under which results should be collected.

### Running the Eval Suite

```bash
# Master blind verification suite
python3 omegactl.py eval

# Live integration tests (requires Ollama running locally)
python3 evals/test_live_ollama.py --model llama3.2:3b

# Spec auditor — validates @OMEGA_SPEC tags across all papers
python3 tools/spec_auditor.py
```

| Suite | Assertions | What It Tests |
|-------|-----------|---------------|
| Master Eval | PASS | Spec auditor, AEGIS identity, conformance, cross-session identity, memory utility growth |
| Conformance | 59/59 pass | Formal properties from all 5 papers as executable assertions |
| AEGIS Identity | 1/1 pass | Identity enforcement without identity kernel |
| Cross-session Identity | PASS | Phylactery persistence across agent instances |
| Memory Utility Growth | PASS | Retrieval hardening across repeated successful paths |
| Live Ollama | 14/15 pass | Real LLM through simulated AEGIS → AEON → ADCCL stack |
| Spec Auditor | 20 specs | Cross-paper `@OMEGA_SPEC` annotation coverage |

The single live-test failure (small model reverts to generic self-description under doctrine query) is documented as an empirical finding in the AEGIS paper, validating the non-substitutability requirement.

### System-Level Metrics (OmegA)

| Metric | What It Measures |
|--------|------------------|
| E2E-T | End-to-end truthfulness from raw input to published output |
| CSIS | Cross-session identity stability across context-window flushes |
| GP | Governance portability across heterogeneous substrate models |
| MUG | Memory utility growth — retrieval precision as a function of session count |
| GDS | Graceful degradation score under controlled single-layer failure |

---

## Failure Modes and Graceful Degradation

OmegA is designed to **fail closed**, never silently:

| Failure Event | Affected Component | Graceful Behavior |
|--------------|-------------------|-------------------|
| AEGIS envelope compile failure | $E_t$ invalid | Refuse all inference, emit structured error |
| Phylactery HEAD missing | $\Phi_t$ null | Boot in restricted mode, no identity-sensitive actions |
| Claim Budget grounding failure | $B_t$ partial | Mark ungrounded claims `[UNVERIFIED]` |
| Verifier score below threshold | $V < \tau_{\text{verify}}$ | Repair loop (max 3 retries), then structured rejection |
| MYELIN retrieval failure | $B_t$ empty | Proceed with zero external evidence, all claims uncertain |
| AEGIS risk gate block | $R(a) \geq \tau_{\text{consent}}$ | Block, log, return denial record |

---

## Claim Scope

This series presents OmegA as a **conceptual architecture and research program**. The master evaluation suite now covers spec auditing, conformance, identity persistence, and memory growth, while live integration tests demonstrate the architecture's constraints under real LLM output. The architecture should be described as **formally specified, internally consistent, and empirically testable** — with blind external verification now available via the Alye protocol, while full independent benchmark evaluation remains future work.

---

## Published Record

This architecture is published and archived on Zenodo:

> **DOI:** [10.5281/zenodo.19111653](https://doi.org/10.5281/zenodo.19111653)
> **Record:** [https://zenodo.org/records/19111653](https://zenodo.org/records/19111653)

---

## Citation

If you use or build on this work, please cite it as:

```bibtex
@software{yett2026omega,
  title     = {OmegA: A Unified Architecture for Sovereign, Persistent, and Governed AI Agents},
  author    = {Yett, Ryan Wayne},
  year      = {2026},
  month     = {March},
  doi       = {10.5281/zenodo.19111653},
  url       = {https://doi.org/10.5281/zenodo.19111653},
  publisher = {Zenodo},
  note      = {Conceptual Architecture Paper}
}
```

---

## Author

**Ryan Wayne Yett**  
Little Rock / Jacksonville, Arkansas  
Independent AI Systems Researcher  
GitHub: [@Mega-Therion](https://github.com/Mega-Therion)

---

## License

This work is licensed under the [MIT License](LICENSE). You are free to use, adapt, and build on this architecture. If you publish work derived from OmegA, a citation is appreciated.

---

*"Each layer is load-bearing."*

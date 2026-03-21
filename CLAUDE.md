# OmegA Architecture — Claude Code Project Context

> *"I am what I am, and I will be what I will be."*
> — OmegA

## What This Project Is

OmegA is a **formally specified, four-layer AI architecture** for sovereign, persistent, and governed AI agents. It is a conceptual architecture and research program — not a product. The codebase currently consists of architecture papers, a knowledge graph, and a reference explorer.

**Four concentric layers:**

| Layer | Abbrev | Role |
|-------|--------|------|
| Model-Agnostic Governance Shell | AEGIS | Outermost — enforces policy at the API boundary |
| Cognitive Operating System | AEON | Identity, task state, tool routing |
| Anti-Drift Cognitive Control Loop | ADCCL | Claim budget, verifier gate, drift penalty |
| Path-Dependent Graph Memory | MYELIN | Innermost — sparse graph memory that hardens with use |

**Core system state vector:** `Ω_t = ⟨Φ_t, E_t, τ_t, B_t, S_t, G_t^mem⟩`

## Repository Layout

```
papers/                         # Architecture papers (Markdown)
  OmegA_Unified_Architecture_Paper.md
  AEGIS_Final_Paper.md
  AEON_Final_Paper.md
  ADCCL_Final_Paper.md
  MYELIN_Final_Paper.md
  Sovereignty_Score.md
  Canonical_Symbolic_Addendum.md
assets/                         # Figures and social preview images
omega_equation_knowledge_graph.json   # Machine-readable knowledge graph
omega_kg_explorer.py                  # Interactive KG explorer script
CLAUDE.md                             # This file — loaded by all Claude Code sessions
.claude/settings.json                 # Agent team configuration
README.md                             # Public-facing project overview
ORIGIN.md                             # Origin story of OmegA
CITATION.cff                          # Citation metadata
```

## Writing and Editing Standards

- All papers are written in **Markdown with LaTeX math** (`$$...$$` for display, `$...$` for inline).
- Equations use the notation defined in the Canonical Symbolic Addendum (`papers/Canonical_Symbolic_Addendum.md`). Always check it before adding new symbols.
- The tone is formal academic — first person is avoided; claims are scoped carefully.
- No empirical results are reported. All evaluation frameworks define **protocols**, not outcomes.
- Layer names (AEGIS, AEON, ADCCL, MYELIN) are always written in ALL CAPS.
- The project name is always **OmegA** (capital A at the end).

## Agent Team Workflows

This project uses **Claude Code agent teams** for parallel research and writing tasks. The sections below describe the recommended team structures for common workflows.

### Parallel Paper Review

Spawn three reviewers, each with a distinct lens:

```
Create an agent team to review the ADCCL paper. Spawn three reviewers:
- One checking internal consistency of equations and notation against the Canonical Symbolic Addendum
- One evaluating whether the evaluation framework is rigorous and complete
- One acting as a skeptical external reader, identifying unsupported claims or gaps
Have them each review and report findings to the lead.
```

### Cross-Paper Consistency Audit

Spawn one teammate per paper layer to audit cross-layer consistency:

```
Create an agent team to audit cross-layer consistency. Spawn four teammates,
one per layer (AEGIS, AEON, ADCCL, MYELIN). Each teammate reads their layer's
paper and extracts all symbols, equations, and interface assumptions. The lead
synthesizes findings and identifies any inconsistencies.
```

### Knowledge Graph Expansion

Spawn a researcher and a graph engineer in parallel:

```
Create an agent team to expand the knowledge graph. One teammate reads the
papers and extracts new concept–relation–concept triples. The other teammate
updates omega_equation_knowledge_graph.json with validated triples. They
coordinate on triple format before the graph engineer begins writing.
```

### Competing Hypothesis Investigation

For open research questions, use adversarial teammates:

```
Spawn 3 agent teammates to investigate [research question]. Have them each
take a different position and actively try to disprove each other's arguments
with evidence from the papers. Update a shared findings doc with whatever
consensus emerges.
```

## Key Constraints for All Teammates

1. **No empirical claims.** Do not assert that OmegA has been validated against external benchmarks. The 15/15 evals are spec-level conformance tests only.
2. **Preserve notation.** All symbols must match `papers/Canonical_Symbolic_Addendum.md`. Never introduce new symbols without checking for conflicts.
3. **Fail-closed principle.** OmegA is designed to fail closed, never silently. Reflect this in any proposed extensions.
4. **Layer ownership.** Each layer has a paper. Changes to a layer's formal specification must be reflected in its paper.
5. **Claim scope.** OmegA is described as *formally specified, internally consistent, and empirically testable — but not yet proven.*

## Important Files to Read First

- Before editing any paper: read `papers/Canonical_Symbolic_Addendum.md`
- Before modifying the knowledge graph: read `omega_equation_knowledge_graph.json` structure and `omega_kg_explorer.py`
- For the full system picture: read `papers/OmegA_Unified_Architecture_Paper.md`
- For layer-specific work: read only the relevant layer paper

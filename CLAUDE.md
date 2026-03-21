# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

`/home/mega/OmegA-Architecture` is the canonical publication and architecture repository for the OmegA project — a four-layer formally specified architecture for sovereign, persistent, and governed AI agents. It is **not** a service monorepo or runnable application.

**DOI:** 10.5281/zenodo.19111653
**Author:** R.W. Yett (Ryan Wayne Yett) — `github.com/Mega-Therion/OmegA-Architecture`

## Architecture Overview

OmegA is a concentric four-layer system. Layer numbers go from outermost to innermost:

| Layer | Name | Role |
|-------|------|------|
| 1 | **AEGIS** | Model-agnostic governance shell — enforces policy at the API boundary |
| 2 | **AEON** | Cognitive operating system — manages the Phylactery identity chain and task state |
| 3 | **ADCCL** | Anti-drift cognitive control loop — claim budgets and self-tagging |
| 4 | **MYELIN** | Path-dependent graph memory — hardens retrieval paths with use |

The unified system state is: `Ω_t = ⟨Φ_t, E_t, τ_t, B_t, S_t, G_t^mem⟩`

Each layer has a corresponding final paper in `papers/`.

## Key Files

- `README.md` — full architecture overview with equations and layer descriptions
- `ORIGIN.md` — canonical origin document (the DeepSeek Challenge, Dec 31 2025)
- `CITATION.cff` — citation metadata for academic use
- `papers/OmegA_Unified_Architecture_Paper.md` — the master unified paper
- `papers/MYELIN_Final_Paper.md`, `ADCCL_Final_Paper.md`, `AEON_Final_Paper.md`, `AEGIS_Final_Paper.md` — per-layer papers
- `papers/Canonical_Symbolic_Addendum.md` — canonical symbol table and equation reference
- `papers/Sovereignty_Score.md` — scoring framework
- `omega_equation_knowledge_graph.json` — graph of all formal equations and symbols
- `omega_kg_explorer.py` — CLI tool for querying the knowledge graph

## Knowledge Graph Explorer

```bash
python3 omega_kg_explorer.py <search_term>      # search nodes/labels
python3 omega_kg_explorer.py --list-nodes       # list all nodes
python3 omega_kg_explorer.py --list-edges       # list all edges
python3 omega_kg_explorer.py --layer MYELIN     # filter by layer (MYELIN|ADCCL|AEON|AEGIS)
```

## Default Work Mode

All normal work starts in this repo. Priority tasks:
- Editing and improving papers (publication quality: precise, formal, cross-referenced)
- Maintaining cross-references between papers and the knowledge graph
- Updating `CITATION.cff` and `README.md` for accuracy
- Adding or revising `assets/` for figures and diagrams

## Archive

`/home/mega/ATTIC/OmegA-cutover-20260319-233802` is the pre-cutover archive. Consult it only for historical recovery — never as a source of truth for current architecture.

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

## External Verification Package

For blind testers and outside reviewers:
- `publication/EXTERNAL_VERIFICATION.md` — what OmegA claims, how to verify it end-to-end
- `publication/ALYE_ONBOARDING.md` — numbered test sequence, no prior context assumed
- `publication/SELF_DESCRIPTION_CONTRACT.md` — canonical self-description with honest limits
- `publication/CLAIM_LEDGER.md` — Proven / Demonstrable / Conditional / Not Claimed table
- `publication/VERIFICATION_RUBRIC.md` — pass/fail rubric for each claim
- `publication/GAP_REPORT.md` — unbacked claims and tests that would close each gap

## Key Files

- `README.md` — full architecture overview with equations and layer descriptions
- `ORIGIN.md` — canonical origin document (the DeepSeek Challenge, Dec 31 2025)
- `CITATION.cff` — citation metadata for academic use
- `catalog/INDEX.md` — canonical folder policy and card-catalog index
- `catalog/registry.json` — machine-readable directory registry
- `publication/RELEASE.md` — publication front door for public vs reviewer-gated bundles
- `publication/PUBLICATION_SET.md` — canonical publication map across the corpus
- `publication/exports/INDEX.md` — export-ready handoff artifacts
- `scripts/render_publication_exports.py` — render the publication export tracks to PDF
- `scripts/publication_release.sh` — one-command publication export wrapper
- `publication/PUBLIC_RELEASE_BUNDLE.md` — redaction-safe bundle for public release
- `publication/PRIVATE_REVIEW_BUNDLE.md` — broader reviewer-gated bundle
- `scripts/catalog_sync.py` — regenerate or validate the registry from the repo tree
- `scripts/memory_gate.py` — fast memory-only gate for retrieval and store regressions
- `tools/proof_auditor.py` — executable drift check for theorem / claim / proof correspondence
- `verify.sh` — canonical release gate; auto-switches to `scripts/memory_gate.py` for memory-only diffs
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
- Read `catalog/INDEX.md` first when deciding where new artifacts belong.
- Use `scripts/catalog_sync.py --write` to regenerate `catalog/registry.json` from the repo tree before creating a new top-level folder.
- Update the catalog and `scripts/catalog_guard.py` whenever a new structural folder is added.
- Use `python3 scripts/memory_gate.py` when you only need the memory-store regression gate.
- Use `python3 omegactl.py eval` as the canonical blind verification master eval.
- Editing and improving papers (publication quality: precise, formal, cross-referenced)
- Maintaining cross-references between papers and the knowledge graph
- Updating `CITATION.cff` and `README.md` for accuracy
- Maintaining `publication/RELEASE.md` and the publication bundles as the front door for new agents
- Adding or revising `assets/` for figures and diagrams

## Folder Policy

- Every persistent artifact has one canonical home.
- New top-level folders are not created ad hoc; they must be registered first.
- Scratch work goes in `INBOX/` or a temporary workspace, never in source roots.
- Generated outputs stay isolated in `output/`, `distilled/`, `evals/`, or `reports/` as appropriate.

## Archive

`/home/mega/ATTIC/OmegA-cutover-20260319-233802` is the pre-cutover archive. Consult it only for historical recovery — never as a source of truth for current architecture.

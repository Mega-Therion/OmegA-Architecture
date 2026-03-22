# Repository Guidelines

## Canonical Scope
- This repository is the canonical OmegA source of truth going forward.
- It is a publication and architecture repo, not the older implementation monorepo.
- Historical OmegA material lives in `/home/mega/ATTIC/OmegA-cutover-20260319-233802` and should be treated as archive-only unless explicitly requested.

## Main Contents
- `README.md`: architecture overview and canonical framing.
- `ORIGIN.md`: canonical origin document.
- `papers/`: formal paper series and addenda.
- `assets/`: publication figures and graphics.
- `omega_equation_knowledge_graph.json`: graph data artifact.
- `omega_kg_explorer.py`: local utility for graph exploration.

## Working Priorities
- Improve clarity, rigor, consistency, and publication quality.
- Preserve canonical terminology across papers and overview docs.
- Keep changes aligned with the repo’s role as the publication/reference source, not as a staging ground for reviving archived runtime code.

## Change Style
- Prefer small, defensible edits.
- Keep prose precise and internally consistent.
- When making structural changes across papers, ensure terminology and equations stay aligned.

## Shell Protocol
- When giving shell commands to the user, write them to a file first and provide one copy-paste line to run.

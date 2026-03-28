# OmegA Catalog

This directory is the canonical index-card layer for the repository.

## Rules

- One artifact has one canonical home.
- Every top-level directory must be registered here before it is treated as valid.
- New work starts by reading this index, then the relevant card, then the source-of-truth files.
- Scratch work belongs in `INBOX/` or a temporary workspace, never in canon.
- Generated outputs stay in their own output layer and do not become new source roots.

## Read Order

1. `catalog/INDEX.md`
2. The relevant `catalog/card-template.md` entry or registry entry
3. The owning subsystem docs
4. The source file or runtime surface

## Canonical Top-Level Map

- `catalog/` - registry and card catalog for the repo
- `canon/` - immutable doctrine and policy layer
- `specs/` - machine-readable contracts and schemas
- `omega/` - Python core runtime package
- `runtime/` - Rust CLI, service assets, and runtime build layers
- `web/` - Next.js product surface and deployment app
- `mcp/` - MCP server implementation
- `tools/` - reusable internal utilities and analysis scripts
- `scripts/` - one-off operational and migration scripts
- `evals/` - harnesses, regression suites, and evidence outputs
- `reports/` - benchmark and analysis reports
- `docs/` - operator documentation and build briefs
- `papers/` - technical papers and formal drafts
- `publication/` - release-ready written assets and bundles
- `history/` - append-only narrative and provenance log
- `assets/` - images and media artifacts
- `distilled/` - derived structured datasets
- `output/` - generated outputs and transcripts
- `voice/` - voice runtime and helper files
- `alexa/` - Alexa skill artifacts
- `roadmap/` - future plans and sequencing
- `.claude/` - local agent configuration and wrapper assets
- `.github/` - CI and repository automation
- `.vercel/` - deployment metadata and Vercel linkage
- `policies/` - local policy profiles for runs and checks
- `schemas/` - JSON schemas for runtime and validation

## Card Format

Use `catalog/card-template.md` for any new card entry.

Each card should answer:

- What lives here?
- What must never live here?
- What reads this first?
- What is the canonical owner?
- What validates it?

## Adding New Structure

1. Decide whether the artifact belongs in an existing home.
2. If not, add a new card and registry entry here first.
3. Update the owning subsystem docs.
4. Regenerate `catalog/registry.json` with `python3 scripts/catalog_sync.py --write`.
5. Add or update the validation script if the new folder is structural.
6. Only then create the directory or file.

## Anti-Drift Policy

- No random top-level folders.
- No duplicate homes for the same artifact class.
- No generated outputs promoted to source roots.
- No silent folder creation without a catalog entry.
- Re-run `python3 scripts/catalog_sync.py --write` after any structural folder change.

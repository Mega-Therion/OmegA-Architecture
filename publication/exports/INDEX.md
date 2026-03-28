# OmegA Sovereign
## Export-Ready Publication Artifacts

This directory holds the handoff-ready publication outputs for the OmegA corpus.

The files here are intentionally short, stable, and conversion-friendly so a new agent can export the publication package without reconstructing structure from the longer source papers.

## Canonical Export Artifacts

- `publication/exports/PUBLIC_RELEASE_EXPORT.md`
  - Public-facing export front page for the redaction-safe bundle.
- `publication/exports/PRIVATE_REVIEW_EXPORT.md`
  - Trusted-review export front page for the broader reviewer bundle.
- `publication/exports/OMEGA_MASTER_ONE_PAGER.md`
  - Condensed one-page synthesis of the core state equation, control loop, and publication claim.
- `publication/exports/README.md`
  - Handoff guide for regenerating the export PDFs.

## Source Bundles

The export artifacts above are derived from, but do not replace, the canonical source bundles:

- `publication/PUBLIC_RELEASE_BUNDLE.md`
- `publication/PRIVATE_REVIEW_BUNDLE.md`
- `publication/OMEGA_MASTER_SYNTHESIS.md`

## Use Rule

- Use the source bundles when editing content.
- Use the export artifacts when handing off, publishing, or converting the corpus into PDF or another presentation format.
- Use `python3 scripts/render_publication_exports.py --all` to emit the PDF bundles into `output/publication/`.
- Use `bash scripts/publication_release.sh` as the one-command canonical wrapper.

# OmegA Publication Export Handoff

This directory contains the export-ready front pages for the OmegA publication corpus.

## What Each File Is For

- `PUBLIC_RELEASE_EXPORT.md`
  - Public-facing cover page for the redaction-safe bundle.
- `PRIVATE_REVIEW_EXPORT.md`
  - Reviewer-facing cover page for the broader corpus.
- `OMEGA_MASTER_ONE_PAGER.md`
  - Condensed one-page synthesis of the core claim, equation, and control loop.

## How To Regenerate The PDFs

Run the canonical release wrapper from the repo root:

```bash
bash scripts/publication_release.sh
```

That command emits the PDF bundles into `output/publication/`.

If you want the underlying renderer directly, use:

```bash
python3 scripts/render_publication_exports.py --all
```

## Source Of Truth

These export files are derived from the canonical source bundles:

- `publication/PUBLIC_RELEASE_BUNDLE.md`
- `publication/PRIVATE_REVIEW_BUNDLE.md`
- `publication/OMEGA_MASTER_SYNTHESIS.md`

Do not edit the export files to change meaning. Update the source bundles first, then regenerate the export artifacts.

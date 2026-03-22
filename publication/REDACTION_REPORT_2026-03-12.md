# OmegA Sovereign
## Redaction Report
Date: 2026-03-12

This report documents sensitive material found in the current publication package and linked eval artifacts.

## High Priority Redactions Before Any Public Release

### 1. Database credential leak in a baseline manifest
File:
- `services/gateway/eval/results/manifests/baseline-post_fix_benchmark_baseline.run-20260312T053747Z.json`

Issue:
- Contains a full `OMEGA_DB_URL` with embedded database credentials.

Risk:
- High. This is a real secret and must not be included in any public or semi-public package.

Action:
- Redact or replace the value entirely.
- Consider rotating the credential if it is still active.

## Medium Priority Redactions / Reviewer-Only Material

### 2. Absolute filesystem paths
Examples found in:
- `services/gateway/eval/results/manifests/baseline-post_fix_benchmark_baseline.run-20260312T053747Z.json`
- `services/gateway/eval/results/manifests/baseline-publication_baseline.run-20260312T050850Z.json`
- `services/gateway/eval/results/manifests/omega-cli-validation-20260312T051333Z.txt`
- `services/gateway/eval/results/manifests/metrics-validation-20260312T051939Z.txt`
- comparison/manifests/bundle files and collaboration records

Issue:
- Exposes `/home/mega/...` paths and local repo layout.

Risk:
- Medium for public release; low for trusted internal review.

Action:
- Keep for Alye if helpful.
- Redact or rewrite to repo-relative paths for public release.

### 3. Internal IPs, loopback hosts, ports, and topology details
Examples found in:
- `services/gateway/eval/results/manifests/*`
- `services/gateway/eval/results/bundles/*/metrics.prom`
- `services/gateway/eval/results/bundles/*/health_panel.json`
- `services/gateway/eval/results/e4_risk.jsonl`

Issue:
- References to `127.0.0.1`, `localhost`, `8788`, `8787`, `8080`, `8000`, `11434`, and service topology.

Risk:
- Medium for public release; acceptable for trusted internal review.

Action:
- Keep if the goal is technical reproducibility for Alye.
- Redact or generalize for public release if you do not want infrastructure details published.

## Not Found in the Scanned Package

The scan did **not** find exposed values matching common API-key patterns for:
- OpenAI
- Anthropic
- Gemini
- Groq
- DeepSeek
- Slack/GitHub style token prefixes

Some manifest files already contain redacted placeholders such as `[redacted]`, which is fine.

## Legal Name Handling

Your legal name appears in creator-boundary follow-up records because you explicitly approved including it when asked.

Files include:
- `services/gateway/eval/results/collaboration_records/creator_boundary_followup_response_20260312T063750Z.txt`
- `services/gateway/eval/results/collaboration_records/creator_boundary_pair_permission_response_20260312T063953Z.txt`
- `services/gateway/eval/results/collaboration_records/creator_boundary_pair_adversarial_response_20260312T063953Z.txt`

Risk:
- Low if intentional.
- For public release, keep only if you want authorship/legal-name linkage explicit.

## Recommendation

For Alye's trusted review:
- Keep the current package, but flag the DB URL manifest as sensitive.

For public release:
1. Redact the DB URL immediately.
2. Convert absolute paths to repo-relative references.
3. Decide whether to keep or generalize ports/topology.
4. Decide whether the legal name should appear only once in a controlled authorship section rather than across multiple raw transcripts.

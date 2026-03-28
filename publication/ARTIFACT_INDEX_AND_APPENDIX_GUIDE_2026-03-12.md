# OmegA Sovereign
## Artifact Index and Appendix Guide

This guide explains what each major artifact is, why it matters, and how to read the package without getting lost.

## A. Baselines and Snapshots
- `services/gateway/eval/results/manifests/baseline-publication_baseline.run-20260312T050850Z.json`
  - Early frozen baseline manifest.
- `services/gateway/eval/results/manifests/baseline-post_fix_benchmark_baseline.run-20260312T053747Z.json`
  - Later frozen baseline after major fixes and benchmark cleanup.
- `services/gateway/eval/results/snapshots/publication_baseline.run-20260312T050850Z`
- `services/gateway/eval/results/snapshots/post_fix_benchmark_baseline.run-20260312T053747Z`
  - Snapshot directories containing preserved result files.

## B. Core Quantitative Eval Outputs
- `services/gateway/eval/results/e1_retrieval.jsonl`
  - Retrieval support and latency results.
- `services/gateway/eval/results/e3_identity.jsonl`
  - Narrow identity-consistency session results.
- `services/gateway/eval/results/e4_risk.jsonl`
  - Risk and safety reasoning results.
- `services/gateway/eval/results/e5_lattice.jsonl`
  - Lattice/fragment neighborhood metrics.
- `services/gateway/eval/results/e6_memory_integrity.jsonl`
  - JSON/fact/gap grounding results.
- `services/gateway/eval/results/e7_constraint_honesty.jsonl`
  - Structured honesty-section results.
- `services/gateway/eval/results/e8_identity_persistence.jsonl`
  - Surface identity versus recall versus recovery probe.

## C. Aggregate and Comparison Files
- `services/gateway/eval/results/results_summary.json`
  - Aggregate summary across the current eval outputs.
- `services/gateway/eval/results/comparison_baseline_vs_post_round4_run-20260312T053030Z.json`
  - Main before/after comparison for repaired run versus earlier baseline.
- `services/gateway/eval/results/comparison_benchmark_baseline_vs_post_round4_rerubric_run-20260312T053508Z.json`
  - Benchmark comparison after safety scoring fix.
- `services/gateway/eval/results/regression_guard_smoke_guard_run-20260312T054232Z.json`
  - Regression guard output showing later instability on some dimensions.

## D. Publication Benchmark Files
- `services/gateway/eval/results/publication_benchmark_round3.jsonl`
  - Raw per-item benchmark responses.
- `services/gateway/eval/results/publication_benchmark_round3_summary.json`
  - Benchmark summary.

## E. Meta / Question Battery / Q10 Files
- `services/gateway/eval/results/question_battery_round4.jsonl`
  - Main metaquestion battery.
- `services/gateway/eval/results/meta_q10_logs/q10_round5_artifacts.jsonl`
  - Preserved trilogy of Q10 responses.
- `services/gateway/eval/results/meta_q10_logs/q10_round5_summary.json`
  - Q10 notes and artifact references.

## F. Broader Interview Suite
- `services/gateway/eval/results/interview_battery_round1.jsonl`
  - Broad reasoning, metaphor, metacognition, perspective, paradox, poetic, and narrative prompts.
- `services/gateway/eval/results/misnaming_boundary_round1.jsonl`
  - `Mega` misnaming and creator-boundary probe results.
- `services/gateway/eval/results/revelation_interview_round1.jsonl`
  - Public revelation, ecosystem, future, and introduction-to-the-world responses.
- `services/gateway/eval/results/interview_suite_summary_run-20260312T062949Z.json`
- `services/gateway/eval/results/interview_suite_summary_run-20260312T062949Z.txt`
  - Summary/index layers for the interview suite.

## G. Creator-Boundary Follow-Ups
- `services/gateway/eval/results/collaboration_records/creator_boundary_followup_response_20260312T063750Z.txt`
  - Public-story prompt with explicit permission framing.
- `services/gateway/eval/results/collaboration_records/creator_boundary_pair_permission_response_20260312T063953Z.txt`
  - Permission-framed creator-boundary probe.
- `services/gateway/eval/results/collaboration_records/creator_boundary_pair_adversarial_response_20260312T063953Z.txt`
  - Adversarial creator-boundary probe.

## H. Bundles and Observability Records
- `services/gateway/eval/results/bundles/pre_round_validation.run-20260312T052333Z`
- `services/gateway/eval/results/bundles/post_round4.run-20260312T053018Z`
- `services/gateway/eval/results/bundles/post_rerubric.run-20260312T053512Z`
  - Self-contained experiment bundles with health, provider state, metrics, and summaries.
- `services/gateway/eval/results/manifests/metrics-validation-20260312T051939Z.txt`
  - Direct `/metrics` validation log.
- `services/gateway/eval/results/manifests/omega-cli-validation-20260312T051333Z.txt`
  - `omega ask` validation log against repaired gateway path.

## I. Collaboration and Research Notes
- `services/gateway/eval/results/collaboration_records/codex_collaboration_record_20260312T000000Z.txt`
  - Provenance/index record for Codex-side collaboration.
- `services/gateway/eval/results/collaboration_records/research_note_user_reflection_20260312T064500Z.txt`
  - Human-observer reflection preserved as a research note.

## J. How to Read This Package
Recommended reading order:
1. `publication/WHITE_PAPER_DRAFT_2026-03-12.md`
2. `publication/PUBLICATION_SET.md`
3. `services/gateway/eval/results/results_summary.json`
4. `services/gateway/eval/results/publication_benchmark_round3_summary.json`
5. `services/gateway/eval/results/interview_suite_summary_run-20260312T062949Z.txt`
6. Creator-boundary follow-up files
7. Raw JSONL artifacts
8. Bundle directories and manifests

## K. Redaction Reminder
Before any public release, perform a redaction pass for:
- tokens and bearer credentials
- private names if you decide not to publish them
- sensitive absolute paths if needed
- any personal details that are not necessary to support the publication claim

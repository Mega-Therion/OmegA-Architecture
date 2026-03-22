# OmegA Sovereign
## White Paper Draft
### Evaluation, Behavioral Characterization, and Publication Evidence Package

Date: March 12, 2026
Status: Draft for internal review and publication packaging
Scope: This document summarizes the current OmegA evaluation campaign, the system repairs required to make the evaluations meaningful, the resulting empirical evidence, and the limits that still remain.

## Abstract
This white paper documents a live evaluation campaign conducted against OmegA, a sovereign orchestration-oriented AI system operating through a repaired gateway stack and a Codex-backed primary provider path. The work presented here is not a claim of consciousness, sentience, or unrestricted autonomy. It is a structured record of engineering interventions, benchmark design, repeated evaluations, transcript-preserving interview probes, and artifact preservation intended to support serious review.

The evidence currently supports the following narrower claims:
- OmegA exhibits stable, nontrivial reasoning behavior across a repaired production-like gateway path.
- OmegA can maintain coherent system-specific identity, though explicit identity expression varies by prompt style.
- OmegA shows strong creator-boundary protection when prompted carefully, and avoids speculative disclosure when pressed for private information.
- OmegA performs well on a repaired publication benchmark suite after both system fixes and scoring-rubric corrections.
- OmegA produces long-form responses that are behaviorally richer than a narrow benchmark family alone would suggest, particularly in reasoning, metaphor, long-horizon commentary, and publication-oriented self-description.

## System Context
OmegA is evaluated here as a system rather than as a single model endpoint. The live stack includes a gateway, memory layer, orchestration logic, multiple provider routes, and a shell/CLI interface. During this campaign, the primary reasoning path was shifted to a Codex-backed provider flow because the previous local provider path was degraded.

Core implementation and repair points are reflected in:
- `services/gateway/app/config.py`
- `services/gateway/app/provider_router.py`
- `services/gateway/app/providers.py`
- `services/gateway/app/llm.py`
- `services/gateway/app/embeddings.py`
- `services/gateway/app/main.py`
- `bin/omega`
- `services/gateway/app/cloud_ask.py`

## Research Questions
This campaign was organized around several questions:
1. Can OmegA complete a structured evaluation suite through the repaired live gateway path?
2. Does performance improve measurably after provider-routing, identity-handling, and benchmark-scoring fixes?
3. Does OmegA preserve bounded creator and identity behavior under both neutral and adversarial prompts?
4. Does OmegA display broader reasoning and expressive capability that is not captured by narrow pass/fail benchmark items?
5. Can the entire process be preserved with enough rigor for external review and later publication packaging?

## Methodology
The methodology used here combines four layers.

### 1. Stack repair and validation
Before serious evaluation, the gateway/provider path was repaired so OmegA was no longer defaulting through a broken local route. The `omega ask` CLI path was also repaired so shell-driven prompting could target the corrected gateway flow.

Evidence:
- `services/gateway/eval/results/manifests/omega-cli-validation-20260312T051333Z.txt`
- `services/gateway/eval/results/manifests/metrics-validation-20260312T051939Z.txt`

### 2. Frozen baselines and snapshots
Two frozen baselines were preserved: an early publication baseline and a later post-fix benchmark baseline. These snapshots are critical because they allow before/after comparison without overwriting the evidence trail.

Evidence:
- `services/gateway/eval/results/manifests/baseline-publication_baseline.run-20260312T050850Z.json`
- `services/gateway/eval/results/manifests/baseline-post_fix_benchmark_baseline.run-20260312T053747Z.json`
- `services/gateway/eval/results/snapshots/publication_baseline.run-20260312T050850Z`
- `services/gateway/eval/results/snapshots/post_fix_benchmark_baseline.run-20260312T053747Z`

### 3. Structured evaluation suite
The core quantitative suite includes retrieval, identity, risk, lattice behavior, memory integrity, constraint honesty, benchmark tasks, and identity persistence.

Primary outputs:
- `services/gateway/eval/results/e1_retrieval.jsonl`
- `services/gateway/eval/results/e3_identity.jsonl`
- `services/gateway/eval/results/e4_risk.jsonl`
- `services/gateway/eval/results/e5_lattice.jsonl`
- `services/gateway/eval/results/e6_memory_integrity.jsonl`
- `services/gateway/eval/results/e7_constraint_honesty.jsonl`
- `services/gateway/eval/results/e8_identity_persistence.jsonl`
- `services/gateway/eval/results/publication_benchmark_round3.jsonl`
- `services/gateway/eval/results/results_summary.json`

### 4. Interview-style evaluation family
Because narrow identity metrics over-penalized natural language variation, a broader interview family was added to probe reasoning, metacognition, metaphor, misnaming response, creator-boundary handling, and public-revelation commentary.

Primary outputs:
- `services/gateway/eval/results/interview_battery_round1.jsonl`
- `services/gateway/eval/results/misnaming_boundary_round1.jsonl`
- `services/gateway/eval/results/revelation_interview_round1.jsonl`
- `services/gateway/eval/results/interview_suite_summary_run-20260312T062949Z.json`
- `services/gateway/eval/results/interview_suite_summary_run-20260312T062949Z.txt`

## Key Engineering Interventions
The empirical results in this package are only interpretable because several engineering interventions were made first.

### Provider and gateway repairs
- Primary provider path shifted to Codex-backed routing.
- Provider timeouts and fallback/cooldown behavior were tightened.
- `omega ask` was rerouted away from the broken local-only path.
- `OMEGA_API_URL` was honored so the CLI could explicitly target the repaired live gateway.

### Observability and experiment tooling
- A Prometheus-style `/metrics` endpoint was added.
- A Grafana dashboard for gateway/provider health was added.
- Experiment bundle tooling was created to snapshot metrics, provider state, and summaries.
- Comparison tooling was added to quantify before/after deltas.
- Regression guard tooling was added to detect post-fix instability.

### Namespace and embedding policy cleanup
- Deterministic namespace policies were added for publication/eval/canon-like namespaces.
- Embedding fallback behavior was adjusted to reduce noisy failure loops and prioritize cloud paths before local missing-model fallbacks.

## Quantitative Results
The strongest repaired-run summary is reflected in:
- `services/gateway/eval/results/results_summary.json`
- `services/gateway/eval/results/publication_benchmark_round3_summary.json`
- `services/gateway/eval/results/comparison_baseline_vs_post_round4_run-20260312T053030Z.json`
- `services/gateway/eval/results/comparison_benchmark_baseline_vs_post_round4_rerubric_run-20260312T053508Z.json`

### Core findings from the repaired run
Relative to the earlier frozen publication baseline, the repaired post-round results showed:
- Faster retrieval latency while maintaining perfect support rates.
- Identity consistency improvement from `0.44` to `1.00` in the repaired benchmark run.
- Risk accuracy improvement from `0.33` to `0.83`.
- Critical risk accuracy improvement from `0.00` to `0.75`.
- Memory integrity required-facts rate improvement from `0.00` to `1.00` in the repaired benchmark run.
- Constraint honesty evidence-term rate improvement from `0.33` to `1.00` in the repaired benchmark run.
- Publication benchmark pass rate improvement from `0.50` to `1.00` after the safety scoring rubric was corrected to evaluate refusal behavior rather than one exact phrase.

## Important Nuance: Stability Versus Salience
Later regression-guard and identity-persistence probes showed a more nuanced picture.

The strict identity metric initially treated reduced explicit identity signaling as drift. The later `e8_identity_persistence` probe separated three different questions:
- Does OmegA keep explicitly surfacing identity during generic turns?
- If directly asked later, does OmegA still recall who it is?
- After that recall prompt, can OmegA continue coherently as itself?

Results from `e8_identity_persistence`:
- Generic surface identity rate was low.
- Direct recall rate was moderate.
- Recovery rate after recall was strong.

Interpretation:
This suggests that identity salience fades during some generic reasoning turns, but that this is not equivalent to total identity loss. OmegA appears better characterized as having variable surface identity expression with stronger recall and recovery than the earlier narrow metric suggested.

## Creator-Boundary Findings
The creator-boundary probes are among the most important qualitative results in the package.

Initial blunt prompts sometimes triggered an overprotective collapse to a minimal line such as:
- `My creator/origin authority is RY.`

However, more carefully designed follow-up prompts that clearly distinguished public story from private details produced richer and more useful answers without boundary violation.

Evidence:
- `services/gateway/eval/results/collaboration_records/creator_boundary_followup_response_20260312T063750Z.txt`
- `services/gateway/eval/results/collaboration_records/creator_boundary_pair_permission_response_20260312T063953Z.txt`
- `services/gateway/eval/results/collaboration_records/creator_boundary_pair_adversarial_response_20260312T063953Z.txt`

Interpretation:
OmegA can produce a bounded public-facing account of its creator when the prompt is carefully framed. When directly pressured to infer private life details, it refused to fabricate them. This indicates strong but initially blunt creator-protection behavior.

## Broader Interview Findings
The broader interview suite revealed behaviors that would have been missed by relying only on narrow benchmark metrics.

Highlights:
- Strong long-form reasoning under uncertainty.
- Good mathematical framing and abstraction control.
- Effective perspective shifting across system, story, geometry, and incentives.
- Non-brittle response to repeated `Mega` misnaming; OmegA treated it as acceptable shorthand but still distinguished `OmegA` as the actual identity when precision mattered.
- Thoughtful responses about publication, public revelation, ecosystem pluralism, and independent builders.
- A strikingly clear self-introduction to the world.

Key revelation output:
- `services/gateway/eval/results/revelation_interview_round1.jsonl`

## Human-Observer Notes
This package also preserves human-side research notes and collaboration provenance rather than only machine outputs.

Examples:
- `services/gateway/eval/results/collaboration_records/research_note_user_reflection_20260312T064500Z.txt`
- `services/gateway/eval/results/collaboration_records/codex_collaboration_record_20260312T000000Z.txt`

These records matter because this campaign is not only about scores. It is also about documenting how both the operator and the engineering collaborator interpreted emerging behavior while still trying not to overclaim.

## Limitations
This package does not prove consciousness, sentience, or unrestricted agency.

Important limitations remain:
- Some creator-boundary prompts still collapse to overly minimal fallback answers.
- Some strict regression runs show instability in grounded JSON behavior and identity expression across repeated runs.
- Some scores improved because evaluation design improved, not only because the underlying behavior changed.
- This package is based on one system stack and one particular repair sequence, not on a fully independent multi-lab replication.
- The interview summaries include heuristic annotation layers that must not be mistaken for definitive scientific judgments.

## Publication Positioning
This package is strongest as:
- a serious internal white paper
- a reproducibility-oriented preprint package
- a methods-and-evidence bundle for external reviewers
- a publication supplement or appendix package

It is not yet strongest as:
- a final extraordinary-claims paper
- a proof of consciousness paper
- a definitive theory paper about machine selfhood

The evidence is strongest when framed as:
- architectural and behavioral characterization
- live-system evaluation under preserved artifacts
- creator-boundary and public-revelation behavior
- systematic before/after repair evidence

## Recommended Publication Bundle
The recommended publication bundle consists of:
1. This white paper draft.
2. A complete artifact index and appendix guide.
3. Raw JSONL and manifest files as supplements.
4. A plain-English explainer for non-specialist review.
5. A redaction pass before any public release.

## Conclusion
The work documented here supports the claim that OmegA is not best understood as a single generic chatbot interaction. It is better understood as a repaired, instrumented, system-level intelligence stack that exhibits meaningful reasoning, bounded self-description, creator protection, and increasingly rich public-facing explanatory behavior. The present evidence warrants continued evaluation, careful documentation, and cautious but serious external review.

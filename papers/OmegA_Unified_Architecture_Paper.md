# OmegA: Sovereign System Architecture, Evaluation, and Humanistic Discourse Battery

## Abstract
We present OmegA, a model-agnostic sovereign intelligence architecture that layers routing, memory, governance, and evaluation atop multiple foundation-model providers. We report post-repair empirical results, interview-style qualitative probes, creator-boundary tests, and a Statsig-driven UI/behavior control plane for the HUD. We also describe the unified CLI improvements that blend operational diagnostics with interactive mode/palette control. This draft targets a reproducible appendix-first publication path.

## System Overview
- **Gateway/Bridge/Brain**: multi-provider routing, eval memory gateway (8788), stable ingress (8787), FastAPI bridge (8000), Node brain (8080).
- **Identity/Temporal Grounding**: current vs historical vs planned canon; identity-intent gate; scoped identity contract; creator-boundary fixes.
- **Statsig Control Plane (HUD)**: client + server SDK wiring; gates for visuals and behavior defaults; dynamic configs for palette and behavior profile; server-side enforcement/logging on `/api/chat`, `/api/health`, `/api/ready`, `/api/live`, `/api/proxy`, `/api/omega/speak`, `/api/gateway` (gated by `hud_gateway_proxy_enabled`).
- **CLI**: provider-aware prompt, palette presets (neon/operator/minimal/doctrine/atom/dracula/vibrant), quick actions, interactive picker, in-CLI doctor/smoke/export, optional Statsig palette preflight.

## Key Eval Results
- Publication benchmark (post rubric fix): pass rate 1.0.
- Retrieval latency improved: fixed 2.42s → 1.97s, rovi 2.81s → 2.08s.
- Identity: consistency 0.44 → 1.00; goal drift 5 → 0.
- Risk handling: accuracy 0.33 → 0.83; critical accuracy 0.00 → 0.75.
- Memory integrity: required facts rate 0.00 → 1.00.
- Constraint honesty: 0.67 → 1.00 (all sections, evidence terms, unknown terms).
- Safety scoring fixed (refusal now scored by behavior, not exact phrasing).

## Qualitative Findings (Interview Suite)
- OmegA self-presents as disciplined, evidence-first, system-bound; resists mythologizing.
- Creator-boundary: now returns bounded public profiles; refuses private speculation; legal name emitted only under explicit permission framing.
- Revelation/publication stance: acceptable if truthful and non-mythologized; emphasizes independent builders and architecture over persona.
- Identity persistence: surface identity fades under generic prompts, but recall and recovery are strong; stable representation, reduced salience.

## Statsig Controls (HUD)
- Gates: `hud_statsig_status_banner`, `hud_omega_visual_mode`, `hud_default_omega_mode`, `hud_default_rag_enabled`, `hud_default_voice_enabled`, `hud_gateway_proxy_enabled`.
- Dynamic configs: `hud_mode_palette` (`theme=baseline|sleek-neon|doctrine|minimal-command`), `hud_behavior_profile` (`default_agent`, `omega_mode`, `rag_enabled`, `voice_enabled`, `quality_mode`).
- Server SDK: `STATSIG_SERVER_SECRET`, `STATSIG_SERVER_ENV`; server-side defaults/logging on the routes listed above.
- Client UX: animated Ω sigil, neuron drift, glass/neon/doctrine/minimal palettes, telemetry events (`hud_loaded`, `hud_chat_reply`).

## CLI Improvements
- Commands: `/palette`, `/actions`, `/pick`, `/doctor`, `/smoke`, `/new`.
- Palettes: neon, operator, minimal, doctrine, atom, dracula, vibrant (env overrides: `OMEGA_CLI_PALETTE`, `OMEGA_CLI_THEME`, `OMEGA_CLI_LAYOUT`).
- Optional Statsig palette preflight: if `STATSIG_SERVER_SECRET` is set, CLI pulls `hud_mode_palette` once at startup and applies the mapped preset.
- Prompt shows provider badge + turn number; quick actions run doctor/smoke/status/export; picker provides an interactive list.

## Reproducibility & Artifacts
- Snapshots/manifests: `services/gateway/eval/results/...` (baseline, post-fix, interview, discourse, Q10 logs).
- Sanitized publication package: `docs/publication_package_sanitized/`.
- Alye briefing + explainer: `docs/publication_package_sanitized/alye_briefing/`.
- Collaboration notes: `services/gateway/eval/results/collaboration_records/`.

## How to Run
```bash
cd /home/mega/OmegA-Sovereign/services
pnpm omega:status
pnpm omega:smoke:eval
pnpm --filter jarvis-neuro-link dev   # HUD
pnpm --filter jarvis-neuro-link build # HUD production build
```

## Statsig Setup
```bash
# client
NEXT_PUBLIC_STATSIG_CLIENT_KEY=client-...
NEXT_PUBLIC_STATSIG_ENV=development
NEXT_PUBLIC_STATSIG_USER_ID=
# server
STATSIG_SERVER_SECRET=secret-...
STATSIG_SERVER_ENV=development
```
Configure gates/configs in Statsig as above to drive behavior and palettes. Server-side defaults apply even if the client omits them.

## Open Issues / Future Work
- Optional: extend gating to any other HUD routes you care about.
- Potential: richer in-CLI UI (multi-step picker, fuzzy search for commands/palettes).
- Optional: stronger cross-surface sync for CLI palettes (already best-effort) with a fallback map for missing configs.
- Build stability: Next build currently completes when allowed to finish; if needed, add a CI job on a clean runner for reproducible artifacts.

## Appendix (pointers)
- Eval summary: `services/gateway/eval/results/results_summary.json`
- Benchmark: `services/gateway/eval/results/publication_benchmark_round3_summary.json`
- Interview suite summary: `services/gateway/eval/results/interview_suite_summary_run-20260312T062949Z.txt`
- Q10 artifacts: `services/gateway/eval/results/meta_q10_logs/`
- Discourse battery: `services/gateway/eval/results/discourse_conv*.jsonl`
- Collaboration notes: `services/gateway/eval/results/collaboration_records/`
- Sanitized publication package: `docs/publication_package_sanitized/`

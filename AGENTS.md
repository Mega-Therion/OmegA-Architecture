# Repository Guidelines

## Project Structure & Module Organization
This repository is a multi-part system. Keep work in the matching area:
- `web/` - Next.js app, UI, API routes, shared components, hooks, and lib code.
- `mcp/` - TypeScript MCP server entrypoint and build output.
- `runtime/` - Rust workspace for gateway, CLI, memory, provider, and trace crates.
- `evals/` - Python-based tests, conformance checks, and benchmark fixtures.
- `scripts/`, `docs/`, `policies/`, `assets/`, and `tools/` - supporting material and automation.

## Build, Test, and Development Commands
Run commands from the relevant subproject directory:
- `cd web && npm run dev` - start the Next.js app locally.
- `cd web && npm run build` - create a production build.
- `cd web && npm run lint` - run ESLint checks.
- `cd mcp && npm run dev` - run the MCP server in watch mode.
- `cd mcp && npm run build` - compile the MCP server to `dist/`.
- `cd runtime && make build|test|check|fmt|clippy` - build, test, verify, format, or lint the Rust workspace.
- `pytest evals/` - run Python evals and conformance tests.

## Coding Style & Naming Conventions
Use the style already present in each subsystem. TypeScript follows the existing Next.js and ESLint setup in `web/`; prefer clear component and hook names such as `VoiceOrb` and `useVoiceEngine`. Rust code in `runtime/` should stay `cargo fmt` clean and pass `clippy`. Python eval files use `snake_case` names like `test_runtime.py`.

## Testing Guidelines
Add or update tests alongside behavior changes. Prefer focused evals in `evals/` for orchestration and runtime behavior, and component or API-level checks in the relevant subproject. When you change UI behavior, include a build or lint run and, if needed, a screenshot or reproduction note.

## Commit & Pull Request Guidelines
History uses short Conventional Commit-style messages such as `feat: ...`, `fix: ...`, and `perf: ...`. Keep commits scoped to one change. PRs should summarize the change, list the affected subsystem, note the commands you ran, and include screenshots for visible UI updates.

## Security & Configuration Tips
Treat `VAULT/` and any `.env` or key material as sensitive. Do not log secrets or copy them into docs. Use the canonical workspace paths in `OMEGA_WORKSPACE/` and avoid editing archived or generated outputs unless the task explicitly requires it.

## Deployment & Verification
- Use Lovable only for exploratory UI prototyping; commit production work in `web/` and ship through Vercel.
- Before declaring an app ready, verify the local route with `web/scripts/omega-smoke.mjs` using `web/.env.local`.
- Production smoke tests must confirm a real session ID, `x-memory-backend: neon-live`, and a persisted message round trip.
- If Vercel Deployment Protection is enabled, test with an approved bypass or temporarily disable protection in the dashboard.

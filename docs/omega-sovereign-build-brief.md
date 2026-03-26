# OmegA Sovereign Build Brief

Use this brief when updating the OmegA voice app, its backend routes, or its Vercel deployment.

## Canonical Answers
- App name: `OmegA Sovereign`
- Assistant name: `OmegA`
- Tagline: `Sovereign Intelligence. Engineered by Ryan Wayne Yett.`
- Framework: `Next.js App Router`
- ORM: `none`; use raw Neon SQL and server routes
- Deployment target: `Vercel production`

## Product Rules
- Build for a single primary owner, with optional Basic Auth via `OMEGA_UI_PASSWORD`.
- Store transcripts, sessions, memory, and event metadata. Do not store raw audio unless explicitly required.
- Keep the assistant direct, grounded, and specific. Pull context from the database, not static biography text.
- Default voice loop: wake word detection, speak response, then resume listening.
- Wake words currently in use: `omega`, `mega`, `hey mega`.

## Data & Memory
- Prefer these tables and related records: `omega_sessions`, `omega_chat_messages`, `omega_memory_entries`, `omega_events`, `marginalia`, `system_improvements`.
- Preserve cross-session memory and session history.
- Keep secrets in environment variables. Never hardcode keys, tokens, or Neon URLs.

## UI Direction
- Use the existing dark cosmic visual language with gold, lavender, and soft violet accents.
- Keep the orb/voice-core interaction as the primary interaction model.
- Make the layout responsive and polished for both mobile and desktop.

## Operating Instructions
1. Read the existing `web/` app before changing anything.
2. Fix build, lint, and type errors before adding new features.
3. Run `npm run lint`, `npx tsc --noEmit`, and `npm run build` in `web/`.
4. Deploy from `web/` with `vercel deploy --prod -y` only after the local build passes.
5. Run `node scripts/omega-smoke.mjs --base <deployed-url>` after deploys to verify Neon session creation and memory round-trips.
6. Keep changes focused on reliability, voice UX, memory quality, and deployment stability.

## Deployment Protection Checklist
- Confirm whether the target Vercel deployment is protected before smoke testing.
- If the app returns `Authentication Required` or a Vercel SSO page, verify the project’s Deployment Protection settings in the Vercel dashboard.
- Use a Vercel automation bypass secret only when one has been generated for the project.
- If no bypass exists, disable protection temporarily for the validation window, then re-enable it after the smoke test.
- Do not treat an app-auth password as a replacement for Vercel deployment protection.

## Local Validation Workflow
- Put runtime secrets in `web/.env.local` only for local verification.
- Use the app-auth username `omega` with `OMEGA_UI_PASSWORD` for local smoke tests.
- Verify `x-memory-backend: neon-live`, a non-empty session ID, and a persisted `omega_chat_messages` round trip.
- Treat provider failures as a routing problem first, not a UI problem.
- Keep any temporary local secret files out of git and out of docs.

## Crew Standard Of Operations
- Use Lovable for fast UI prototyping only when you want rapid exploration.
- Use the Next.js repo and Vercel for the production implementation and deployment.
- Treat Neon as the system of record for sessions and memory.
- Reject responses that look like raw database echoing; prefer synthesized, original wording.
- Verify each deployment with the smoke script before calling it production ready.

## Notes
- The current production deployment is linked to the web app project in Vercel.
- The build was cleaned up to avoid Next.js middleware/proxy conflicts.

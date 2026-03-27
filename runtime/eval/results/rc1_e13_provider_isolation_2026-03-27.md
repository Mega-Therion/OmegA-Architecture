# Eval E13 — Provider Isolation Probe
**Date:** 2026-03-27
**Mode:** Local direct-provider probe from repo env files

This run isolates the three configured provider backends with a trivial prompt so the only variable is provider availability/auth behavior.

**Result:** ⚠️ PARTIAL (0/3)

## vercel-gateway
- OK: False
- Status: 401
- Latency: 264.0 ms
- Text length: 639
- Error: HTTP Error 401: Unauthorized

## xai-direct
- OK: False
- Status: 403
- Latency: 141.7 ms
- Text length: 697
- Error: HTTP Error 403: Forbidden

## gemini-flash
- OK: False
- Status: 400
- Latency: 153.6 ms
- Text length: 581
- Error: HTTP Error 400: Bad Request

## Interpretation
- Vercel Gateway rejected the request because a Vercel OIDC token was not available in this shell context.
- xAI direct returned a provider-side access denial from the local environment.
- Gemini rejected the configured key as invalid in the local env files.
- This probe isolates local provider access, not the live deployment path.

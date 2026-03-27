# Eval E14 — Deployed Route Isolation
**Date:** 2026-03-27
**Run:** Live deployment route isolation — https://omega-sovereign-jdgjin71d-megas-projects-1fcf4ba6.vercel.app
**Result:** ⚠️ PARTIAL (0/4 usable)

This eval hits the deployed route contracts directly so we can see which endpoint collapses first under the current production build.

**First collapse:** chat

## chat
- Path: `/api/chat`
- Provider: `xai-direct`
- Status: 200
- Latency: 47102.2 ms
- Result: COLLAPSED
- Response excerpt: [OmegA diagnostic] provider xai-direct returned no text after 0 chunks. Attempts: gemini-flash:failed -> vercel-gateway:failed -> xai-direct:selected.
- Details: {"provider_header": "xai-direct", "has_diagnostic": true, "response_length": 150}
- Error: none

## research
- Path: `/api/research`
- Provider: `unknown`
- Status: 500
- Latency: 6740.2 ms
- Result: COLLAPSED
- Response excerpt: {"runId":"run_mn9aw2ul","answer":"[PROVIDER ERROR] No LLM response available.","mode":"abstained","confidence":0,"citations":[],"unresolved":["Reply with exactly one word: OK."],"verified":false,"riskScore":0.1,"provider":"none","providerAt
- Details: {"provider_header": "unknown"}
- Error: HTTP Error 500: Internal Server Error

## synthesize
- Path: `/api/synthesize`
- Provider: `unknown`
- Status: 500
- Latency: 519.2 ms
- Result: COLLAPSED
- Response excerpt: {"error":"Error: All Gemini keys exhausted"}
- Details: {"provider_header": "unknown"}
- Error: HTTP Error 500: Internal Server Error

## refine
- Path: `/api/refine`
- Provider: `unknown`
- Status: 500
- Latency: 463.5 ms
- Result: COLLAPSED
- Response excerpt: {"error":"Error: All Gemini keys exhausted"}
- Details: {"provider_header": "unknown"}
- Error: HTTP Error 500: Internal Server Error

## Interpretation
- A route counts as usable only if it returned a non-empty, parseable, route-shaped answer.
- This eval distinguishes live route behavior from local provider accessibility.
- The first collapsed route is the earliest route in sequence that failed the usable-output criterion.

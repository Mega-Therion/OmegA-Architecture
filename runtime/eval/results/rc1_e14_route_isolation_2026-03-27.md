# Eval E14 — Deployed Route Isolation
**Date:** 2026-03-27
**Run:** Live deployment route isolation — https://omega-sovereign-fmrdsyutd-megas-projects-1fcf4ba6.vercel.app
**Result:** ✅ PASS (4/4 usable)

This eval hits the deployed route contracts directly so we can see which endpoint collapses first under the current production build.

**First collapse:** none

## chat
- Path: `/api/chat`
- Provider: `vercel-gateway`
- Status: 200
- Latency: 43537.7 ms
- Result: USABLE
- Response excerpt: OK
- Details: {"provider_header": "vercel-gateway", "has_diagnostic": false, "response_length": 2}
- Error: none

## research
- Path: `/api/research`
- Provider: `vercel-gateway`
- Status: 200
- Latency: 2988.2 ms
- Result: USABLE
- Response excerpt: Insufficient source evidence to answer confidently. Please provide relevant documents.
- Details: {"provider_header": "unknown", "provider": "vercel-gateway", "providerAttempts": [{"name": "vercel-gateway", "status": "selected"}], "mode": "abstained", "verified": true, "confidence": 0}
- Error: none

## synthesize
- Path: `/api/synthesize`
- Provider: `vercel-gateway`
- Status: 200
- Latency: 3884.9 ms
- Result: USABLE
- Response excerpt: The conversation subtly pivots toward troubleshooting underlying systems rather than summarizing surface-level content.
- Details: {"provider_header": "unknown", "provider": "vercel-gateway", "providerAttempts": [{"name": "vercel-gateway", "status": "selected"}]}
- Error: none

## refine
- Path: `/api/refine`
- Provider: `vercel-gateway`
- Status: 200
- Latency: 4197.4 ms
- Result: USABLE
- Response excerpt: Refine this to be more specific and clear.
- Details: {"provider_header": "unknown", "provider": "vercel-gateway", "providerAttempts": [{"name": "vercel-gateway", "status": "selected"}]}
- Error: none

## Interpretation
- A route counts as usable only if it returned a non-empty, parseable, route-shaped answer.
- This eval distinguishes live route behavior from local provider accessibility.
- The first collapsed route is the earliest route in sequence that failed the usable-output criterion.

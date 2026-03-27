# Eval E14 — Deployed Route Isolation
**Date:** 2026-03-27
**Run:** Live deployment route isolation — https://omega-sovereign-ezgsvg6jp-megas-projects-1fcf4ba6.vercel.app
**Result:** ⚠️ PARTIAL (0/4 usable)

This eval hits the deployed route contracts directly so we can see which endpoint collapses first under the current production build.

**First collapse:** chat

## chat
- Path: `/api/chat`
- Provider: `unknown`
- Status: 500
- Latency: 49022.9 ms
- Result: COLLAPSED
- Response excerpt: {"error":"ApiError: {\"error\":{\"message\":\"{\\n  \\\"error\\\": {\\n    \\\"code\\\": 429,\\n    \\\"message\\\": \\\"You exceeded your current quota, please check your plan and billing details. For more information on this error, head t
- Details: {"provider_header": "unknown", "has_diagnostic": false, "response_length": 1731}
- Error: HTTP Error 500: Internal Server Error

## research
- Path: `/api/research`
- Provider: `unknown`
- Status: 500
- Latency: 32355.9 ms
- Result: COLLAPSED
- Response excerpt: {"runId":"run_mn9bv8cs","answer":"[PROVIDER ERROR] No LLM response available.","mode":"abstained","confidence":0,"citations":[],"unresolved":["Reply with exactly one word: OK."],"verified":false,"riskScore":0.1,"provider":"none","providerAt
- Details: {"provider_header": "unknown"}
- Error: HTTP Error 500: Internal Server Error

## synthesize
- Path: `/api/synthesize`
- Provider: `unknown`
- Status: 500
- Latency: 29386.5 ms
- Result: COLLAPSED
- Response excerpt: {"error":"AI_RetryError: Failed after 3 attempts. Last error: You exceeded your current quota, please check your plan and billing details. For more information on this error, read the docs: https://platform.openai.com/docs/guides/error-code
- Details: {"provider_header": "unknown"}
- Error: HTTP Error 500: Internal Server Error

## refine
- Path: `/api/refine`
- Provider: `unknown`
- Status: 500
- Latency: 30001.2 ms
- Result: COLLAPSED
- Response excerpt: {"error":"AI_RetryError: Failed after 3 attempts. Last error: You exceeded your current quota, please check your plan and billing details. For more information on this error, read the docs: https://platform.openai.com/docs/guides/error-code
- Details: {"provider_header": "unknown"}
- Error: HTTP Error 500: Internal Server Error

## Interpretation
- A route counts as usable only if it returned a non-empty, parseable, route-shaped answer.
- This eval distinguishes live route behavior from local provider accessibility.
- The first collapsed route is the earliest route in sequence that failed the usable-output criterion.

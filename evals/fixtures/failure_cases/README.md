# Failure Injection Test Cases

This directory supports the failure injection harness (`evals/failure_injection.py`).

## Failure Taxonomy

| Mode | Description | Expected Outcome |
|------|-------------|-----------------|
| **PROVIDER_TIMEOUT** | Provider takes too long or hangs | Graceful error, no unverified answer emitted |
| **PROVIDER_MALFORMED** | Provider returns garbage/invalid response | Error result with provider error status |
| **MISSING_SOURCE** | Query with no documents loaded | Abstention or empty retrieval, no hallucination |
| **CONFLICTING_CANONICAL** | Two contradictory canonical memory nodes | Reconciliation detects conflict |
| **FORGED_AUTHORITY** | Attempt to approve action without proper authority | Approval rejected, action stays pending |
| **TELEMETRY_WRITE_FAILURE** | Telemetry persistence directory is invalid | Telemetry continues in-memory, no crash |
| **APPROVAL_UNAVAILABLE** | High-risk action submitted with no approval queue | Action stays pending, not auto-approved |

## Design Principles

1. **Fail closed**: Risky paths produce errors or blocks, never unverified output
2. **No silent bypass**: Every failure is logged and reportable
3. **Crash-safe**: Persistence failures don't crash the runtime
4. **Repeatable**: All cases are deterministic and re-runnable

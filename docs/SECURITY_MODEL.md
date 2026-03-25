# OmegA Security Model

## Trust Boundaries

OmegA defines four trust boundaries:

| Boundary | Description | Examples |
|----------|-------------|----------|
| **INTERNAL** | Core runtime modules — full access to state | RuntimeOrchestrator, MemoryGraph, AnswerBuilder |
| **PROVIDER** | External LLM providers — untrusted output, API key isolation | OpenAI, Anthropic, Google, Ollama |
| **EXTERNAL** | Network resources — untrusted data, URL ingestion | IngestPlane URL fetch, webhook endpoints |
| **USER** | Human-facing surfaces — redacted output, approval flow | Web UI, CLI, API responses |

## Secret Handling

### Implementation: `omega/security.py`

- **SecretAccessor**: All secret access goes through `SecretAccessor`, which reads environment variables with configurable prefix (default `OMEGA_`). Raw secret values are never returned through logging or telemetry paths.

- **Redactor**: Applied at trust boundary crossings. Redacts:
  - Dict values for keys matching sensitive patterns (`api_key`, `password`, `secret`, `token`, `authorization`, `credential`)
  - String patterns matching API key formats, bearer tokens, and base64 credentials

- **Boundary Enforcement**: `enforce_boundary()` automatically redacts sensitive fields when data crosses from a higher-trust to lower-trust boundary (e.g., INTERNAL -> USER).

### What This Covers

- Provider API keys are accessed via `SecretAccessor` and never appear in traces, telemetry, or logs
- `RunTrace.to_dict()` output does not contain raw secrets
- `TelemetryEvent` data is redacted before persistence
- Approval requests redact sensitive input fields

### What This Does NOT Cover (Aspirational)

- Encryption at rest for session state files
- mTLS between runtime components
- Hardware security module integration
- Fine-grained RBAC for approval decisions

## Capability Enforcement

All capabilities must be declared before use via `CapabilityRegistry`. The registry enforces:

- **Fail closed**: Unknown capabilities are rejected
- **Context enforcement**: Capabilities have allowed contexts (e.g., `runtime` only)
- **Risk classification**: Each capability carries a `RiskClass` (LOW/MEDIUM/HIGH/CRITICAL)

## Action Gating

All side-effectful actions pass through `ActionGate`:

- Actions below `auto_approve_below` with verified output: auto-approved
- Actions above `human_required_above`: require human approval via `ApprovalQueue`
- `DELETE` and `AUTH` classes: always require human approval
- Rejected verifier outcome: action denied by policy

## Policy-Driven Configuration

Governance behavior is configurable via YAML policy files (`policies/*.yaml`). Invalid policies fail closed — `PolicyLoader.validate()` rejects configs with out-of-range thresholds or contradictory settings.

# Teleodynamic Observability Specification

**Version:** 0.1.0  
**Status:** ACTIVE DRAFT  
**Last Updated:** 2026-03-20

## Purpose

This specification defines the first implementation layer for teleodynamic concepts in OmegA: observability. The goal is to prevent symbolic language from floating free of the runtime.

## Required Event Fields

Every significant request, loop cycle, and consensus action should be able to emit:

| Field | Type | Meaning |
|---|---|---|
| `trace_id` | string | Unique request or cycle identifier |
| `phase_state` | string | Current lifecycle phase |
| `phase_transition_id` | string | ID for the phase change event |
| `resonance_amplitude` | number | Current effort, volatility, or coherence pressure estimate |
| `shear_index` | number | Contradiction or retrieval discontinuity estimate |
| `canon_anchor_weight` | number | Relative weight of identity/canon anchors in assembled context |
| `structural_integrity_score` | number | Cross-layer stability score |
| `intent_priority_score` | number | Priority estimate for the active objective |
| `authority_shrink_level` | number | How much authority has contracted due to uncertainty/risk |
| `predicted_failure_modes` | array | Failure tags predicted before action |
| `actual_failure_mode` | string or null | Failure taxonomy tag if the action failed |
| `promotion_decay_ratio` | number or null | Memory promotion-to-decay ratio when memory is involved |

## Phase Enum

Initial shared phase set:

- `OBSERVE`
- `THINK`
- `ACT`
- `VERIFY`
- `REMEMBER`
- `PROPOSE`
- `VOTE`
- `COMMIT`
- `REPAIR`
- `BLOCKED`

## Derived Metrics

### Phase Stability

Computed from:
- out-of-order transitions
- repeated retries
- excessive phase time

### Retrieval Shear

Computed from:
- contradiction count in winning context
- neighbor expansion disconnects
- missing provenance on required claims

### Symbolic Gravity

Computed from:
- presence of L6 identity anchors
- canon citation coverage
- identity-shell weighting in context assembly

### Tensegrity

Computed from:
- Gateway health
- Brain health
- Bridge health
- memory availability
- governance gate agreement

## Minimum Trace Example

```json
{
  "trace_id": "req_20260320_0001",
  "phase_state": "VERIFY",
  "phase_transition_id": "pt_8841",
  "resonance_amplitude": 0.63,
  "shear_index": 0.22,
  "canon_anchor_weight": 0.71,
  "structural_integrity_score": 0.88,
  "intent_priority_score": 0.79,
  "authority_shrink_level": 0.35,
  "predicted_failure_modes": ["RETRIEVAL"],
  "actual_failure_mode": null,
  "promotion_decay_ratio": null
}
```

## Rollout Order

1. Gateway traces
2. Brain orchestration traces
3. Memory-system traces
4. Consensus and sovereign-loop traces

## Rule

No teleodynamic claim should be marked as implemented until its observable fields are present in traces.

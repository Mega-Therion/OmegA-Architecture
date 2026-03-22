# Task State Object v2

**Version:** 0.1.0  
**Status:** ACTIVE DRAFT  
**Last Updated:** 2026-03-20

## Purpose

This draft extends the existing OmegA task-state model so that teleodynamic concepts can influence routing and gating without becoming prompt-only folklore.

## Required Fields

| Field | Type | Meaning |
|---|---|---|
| `task_id` | string | Stable identifier |
| `objective` | string | What success actually is |
| `constraints` | array[string] | Hard boundaries |
| `success_criteria` | array[string] | Observable completion conditions |
| `declared_unknowns` | array[string] | Known knowledge gaps before action |
| `urgency` | string | `low`, `normal`, `high`, `critical` |
| `intent_priority_score` | number | Relative task priority |
| `goal_valence_vector` | object | Structured weighting across truth, speed, safety, continuity, and operator preference |
| `authority_shrink_level` | number | Reduction in allowed autonomy due to uncertainty or risk |
| `canon_anchor_weight` | number | Influence of identity and canon anchors |
| `predicted_failure_modes` | array[string] | Expected failure tags before execution |
| `phase_state` | string | Current phase |

## Suggested `goal_valence_vector`

```json
{
  "truth": 1.0,
  "speed": 0.4,
  "safety": 0.9,
  "continuity": 0.8,
  "operator_preference": 0.7
}
```

## Required Behaviors

### Authority Shrink

When uncertainty or risk rises:
- reduce side-effectful autonomy
- increase trace detail
- prefer reversible actions
- prefer explicit evidence citations

### Failure Prediction

Before execution, the system should name likely failure tags from the canonical taxonomy.

### Canon Weighting

High-identity or high-governance tasks should show increased `canon_anchor_weight`.

## Initial Integration Points

- Gateway request envelope
- Brain orchestrator
- ADCCL verifier input
- consensus trigger checks

## Success Condition

The TSO becomes the main carrier for:
- teleo-affective logic
- authority shrinkage
- symbolic gravity
- phase tracking

without requiring those ideas to live only in prompts.

# Concept-to-Implementation Mapping

**Version:** 1.0.0  
**Status:** ACTIVE DRAFT  
**Last Updated:** 2026-03-20

This document translates teleodynamic vocabulary into OmegA-native implementation targets. These concepts are not canonical runtime primitives yet. They become engineering concepts only when they are observable, owned, and testable.

| Concept | Implementation meaning in OmegA | Runtime variable or signal | Subsystem owner | Measurable indicators | First milestone |
|---|---|---|---|---|---|
| `phase` | Explicit lifecycle stage for requests, consensus, and sovereign-loop progression | `phase_state`, `phase_started_at`, `phase_transition_id` | Brain orchestration | phase latency, retry count, out-of-order transitions, completion rate | Normalize one shared phase enum across request handling, TSO lifecycle, and consensus traces |
| `amplitude` | Magnitude of active system effort, volatility, or coherence pressure | `resonance_amplitude`, `omega_score_delta`, `confidence_envelope` | Gateway + measurement loop | score variance, confidence spread, threshold crossings | Persist `resonance_amplitude` beside sovereignty score calculations |
| `topological shear` | Structural mismatch between retrieved context neighborhoods and the task's expected structure | `shear_index`, `retrieval_discontinuity_score` | MYELIN / memory system | contradiction frequency, graph edge churn, retrieval repair rate | Add retrieval-shear metrics to hybrid retrieval logs |
| `symbolic gravity` | Pull exerted by canon, identity anchors, and governance constraints on decision paths | `canon_anchor_weight`, `identity_pull_score` | AEON / phylactery layer | canon citation rate, contamination suppression rate, block rate on high-risk actions | Record explicit L6/identity weighting in context assembly traces |
| `tensegrity` | Cross-layer stability maintained by tension between capability, verification, and governance | `structural_integrity_score`, `gate_balance_vector` | OxySpine Trinity / Brain | graceful degradation success, gate disagreement frequency, consensus bypass count | Implement a Trinity health vector in the sovereign loop |
| `recursive self-reference` | Controlled self-inspection of identity, task state, and likely failure without collapse | `self_model_delta`, `predicted_failure_modes`, `self_reference_depth` | ADCCL | self-model prediction accuracy, false-memory rejection rate, repair-loop success | Ship self-model prediction tests and compare predicted vs actual failure tags |
| `teleo-affective engine` | Goal and priority engine combining task fulfillment, operator intent, urgency, and humility thresholds | `goal_valence_vector`, `intent_priority_score`, `authority_shrink_level` | AEON / task state object | task fulfillment rate, override divergence, uncertainty-triggered authority shrinkage | Extend TSO schema with objective, constraints, success criteria, urgency, and authority fields |
| `geometric metabolism` | Memory growth, pruning, and restructuring over time as a utility economy | `phi_t`, `memory_utility_flux`, `cumulative_phi`, `promotion_decay_ratio` | MYELIN / memory system | promotion-to-prune ratio, decay calibration, retrieval quality over time | Implement importance decay, probation queue, and metabolism logging |

## Immediate Priorities

1. Define one telemetry schema used across Gateway, Brain, Bridge, and memory.
2. Upgrade the Task State Object before adding new symbolic language to prompts.
3. Measure retrieval continuity before claiming any reduction in topological shear.
4. Make identity weighting visible in traces.
5. Add self-model and false-memory evals early.

## Constraint

If a concept cannot be attached to a field, metric, owner, and test, it remains canon language only and must not be presented as implemented architecture.

-- omega-trace migration 0003 — teleodynamic observability fields
-- All fields are nullable so existing rows and older writers remain valid.
ALTER TABLE trace_events ADD COLUMN phase_state                 TEXT;
ALTER TABLE trace_events ADD COLUMN phase_transition_id         TEXT;
ALTER TABLE trace_events ADD COLUMN resonance_amplitude         REAL;
ALTER TABLE trace_events ADD COLUMN shear_index                 REAL;
ALTER TABLE trace_events ADD COLUMN canon_anchor_weight         REAL;
ALTER TABLE trace_events ADD COLUMN structural_integrity_score  REAL;
ALTER TABLE trace_events ADD COLUMN intent_priority_score       REAL;
ALTER TABLE trace_events ADD COLUMN authority_shrink_level      REAL;
ALTER TABLE trace_events ADD COLUMN predicted_failure_modes     TEXT; -- JSON array
ALTER TABLE trace_events ADD COLUMN actual_failure_mode         TEXT;
ALTER TABLE trace_events ADD COLUMN promotion_decay_ratio       REAL;

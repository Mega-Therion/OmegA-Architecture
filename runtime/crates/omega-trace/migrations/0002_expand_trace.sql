-- omega-trace migration 0002 — expand TraceEvent to full orchestration logging spec
-- All new columns are nullable so existing rows remain valid.
ALTER TABLE trace_events ADD COLUMN provider_used         TEXT;
ALTER TABLE trace_events ADD COLUMN retrieval_sources     TEXT;    -- JSON array of memory entry IDs
ALTER TABLE trace_events ADD COLUMN identity_shell_loaded INTEGER; -- boolean (0/1)
ALTER TABLE trace_events ADD COLUMN memory_context_loaded INTEGER; -- boolean (0/1)
ALTER TABLE trace_events ADD COLUMN tool_invocations      TEXT;    -- JSON array of tool names
ALTER TABLE trace_events ADD COLUMN failure_tags          TEXT;    -- JSON array of taxonomy tags
ALTER TABLE trace_events ADD COLUMN consensus_required    INTEGER; -- boolean (0/1)
ALTER TABLE trace_events ADD COLUMN consensus_outcome     TEXT;

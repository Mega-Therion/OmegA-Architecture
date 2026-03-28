-- omega-memory migration 0006 — add retrieval telemetry
-- Adds retrieval_count and last_retrieved_at columns with safe defaults.

ALTER TABLE memory_entries ADD COLUMN retrieval_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE memory_entries ADD COLUMN last_retrieved_at INTEGER;

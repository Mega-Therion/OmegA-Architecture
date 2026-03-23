-- omega-memory migration 0003 — add provenance fields
-- Adds domain, confidence, version, superseded_by, key, and raw_artifact columns.
-- All have safe defaults so existing rows remain valid without modification.

ALTER TABLE memory_entries ADD COLUMN domain TEXT NOT NULL DEFAULT 'operational';
ALTER TABLE memory_entries ADD COLUMN confidence REAL NOT NULL DEFAULT 1.0;
ALTER TABLE memory_entries ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE memory_entries ADD COLUMN superseded_by TEXT;
ALTER TABLE memory_entries ADD COLUMN key TEXT;
ALTER TABLE memory_entries ADD COLUMN raw_artifact TEXT;

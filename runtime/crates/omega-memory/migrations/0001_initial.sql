-- omega-memory initial schema
-- Migration 0001 — creates the memory_entries table and indexes.

CREATE TABLE IF NOT EXISTS memory_entries (
    id          TEXT    PRIMARY KEY,                     -- UUID v4
    content     TEXT    NOT NULL,                        -- the memory text
    source      TEXT    NOT NULL,                        -- "chat" | "agent" | "user" | ...
    importance  REAL    NOT NULL DEFAULT 0.5,            -- 0.0–1.0
    created_at  TEXT    NOT NULL,                        -- ISO 8601 timestamp
    namespace   TEXT    NOT NULL DEFAULT 'default'       -- logical partition
);

CREATE INDEX IF NOT EXISTS idx_memory_namespace   ON memory_entries (namespace);
CREATE INDEX IF NOT EXISTS idx_memory_importance  ON memory_entries (importance DESC);

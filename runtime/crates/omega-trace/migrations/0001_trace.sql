CREATE TABLE IF NOT EXISTS trace_events (
    id          TEXT PRIMARY KEY,
    task_id     TEXT,
    agent       TEXT NOT NULL,
    phase       TEXT NOT NULL,
    action      TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    tokens      INTEGER,
    error       TEXT,
    timestamp   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trace_task  ON trace_events(task_id);
CREATE INDEX IF NOT EXISTS idx_trace_agent ON trace_events(agent);

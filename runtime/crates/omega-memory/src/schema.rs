/// DDL for the `memory_entries` table and indexes.
///
/// This is used by [`crate::sqlite::SqliteMemoryStore::migrate`] as a
/// fallback path when the sqlx migrations directory is not available
/// (e.g., in integration test environments that skip the migrator).
/// The authoritative schema lives in `migrations/0001_initial.sql`.
pub const SCHEMA: &str = r#"
CREATE TABLE IF NOT EXISTS memory_entries (
    id            TEXT    PRIMARY KEY,
    content       TEXT    NOT NULL,
    source        TEXT    NOT NULL DEFAULT 'chat',
    importance    REAL    NOT NULL DEFAULT 0.5,
    created_at    TEXT    NOT NULL,
    namespace     TEXT    NOT NULL DEFAULT 'default',
    embedding     BLOB,
    domain        TEXT    NOT NULL DEFAULT 'operational',
    confidence    REAL    NOT NULL DEFAULT 1.0,
    version       INTEGER NOT NULL DEFAULT 1,
    superseded_by TEXT,
    key           TEXT,
    raw_artifact  TEXT,
    retrieval_count INTEGER NOT NULL DEFAULT 0,
    last_retrieved_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_memory_namespace  ON memory_entries(namespace);
CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory_entries(importance DESC);

CREATE TABLE IF NOT EXISTS agent_wallets (
    agent_id      TEXT    PRIMARY KEY,
    balance       REAL    NOT NULL DEFAULT 0.0,
    total_earned  REAL    NOT NULL DEFAULT 0.0,
    total_spent   REAL    NOT NULL DEFAULT 0.0,
    is_bankrupt   BOOLEAN NOT NULL DEFAULT 0,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_ledger (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id          TEXT    NOT NULL,
    amount            REAL    NOT NULL,
    transaction_type  TEXT    NOT NULL,
    description       TEXT    NOT NULL,
    balance_after     REAL    NOT NULL,
    created_at        TEXT    NOT NULL,
    FOREIGN KEY(agent_id) REFERENCES agent_wallets(agent_id)
);
"#;

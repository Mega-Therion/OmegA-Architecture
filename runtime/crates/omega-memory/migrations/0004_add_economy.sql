-- omega-memory migration 0004 — add economy tables
-- Creates agent_wallets and financial_ledger tables for the Neuro-Credit economy.

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
    transaction_type  TEXT    NOT NULL,  -- Spend, Reward, Fine
    description       TEXT    NOT NULL,
    balance_after     REAL    NOT NULL,
    created_at        TEXT    NOT NULL,
    FOREIGN KEY(agent_id) REFERENCES agent_wallets(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_ledger_agent ON financial_ledger(agent_id);
CREATE INDEX IF NOT EXISTS idx_ledger_time  ON financial_ledger(created_at);

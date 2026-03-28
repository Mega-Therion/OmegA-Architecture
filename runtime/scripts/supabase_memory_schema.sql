-- OmegA Rust Gateway — Supabase memory schema (pgvector)
--
-- Run once in the Supabase SQL editor for your project.
-- The Rust gateway does NOT auto-migrate Postgres.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS omega_memory_entries (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'chat',
    importance  DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    namespace   TEXT NOT NULL DEFAULT 'default',
    embedding   vector(384),
    retrieval_count BIGINT NOT NULL DEFAULT 0,
    last_retrieved_at BIGINT
);

CREATE INDEX IF NOT EXISTS idx_omega_memory_embedding
    ON omega_memory_entries USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_omega_memory_namespace
    ON omega_memory_entries (namespace);

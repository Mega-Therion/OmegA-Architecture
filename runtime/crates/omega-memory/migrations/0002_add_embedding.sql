-- omega-memory migration 0002 — add embedding column
-- Adds a BLOB column to store f32 vector embeddings (little-endian packed).
-- NULL means no embedding has been computed (backward-compatible with existing rows).

ALTER TABLE memory_entries ADD COLUMN embedding BLOB;

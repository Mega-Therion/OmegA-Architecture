-- omega-memory migration 0005 — add tier column to memory_entries
-- Existing rows receive NULL, which maps to Option<String>::None.
ALTER TABLE memory_entries ADD COLUMN tier TEXT;

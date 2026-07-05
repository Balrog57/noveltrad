ALTER TABLE translation_memory ADD COLUMN normalized_hash TEXT;
ALTER TABLE translation_memory ADD COLUMN segment_index INTEGER DEFAULT 0;
ALTER TABLE translation_memory ADD COLUMN is_global INTEGER DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_tm_normalized ON translation_memory(normalized_hash);
CREATE INDEX IF NOT EXISTS idx_tm_global ON translation_memory(is_global) WHERE is_global = 1;

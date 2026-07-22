-- v3 (2026-07-22) — Translation Memory (TMX).
-- Consolidé depuis 001_initial + 010_tm_enhancements + 016_tm_global_nullable.
-- Forme finale : project_id nullable (entrées globales), + normalized_hash,
-- segment_index, is_global.

CREATE TABLE IF NOT EXISTS translation_memory (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
  source_text TEXT NOT NULL,
  target_text TEXT NOT NULL,
  source_language TEXT NOT NULL,
  target_language TEXT NOT NULL,
  usage_count INTEGER NOT NULL DEFAULT 1,
  last_used_at TEXT,
  created_at TEXT NOT NULL,
  normalized_hash TEXT,
  segment_index INTEGER DEFAULT 0,
  is_global INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tm_project_text ON translation_memory(project_id, source_text);
CREATE INDEX IF NOT EXISTS idx_tm_normalized ON translation_memory(normalized_hash);
CREATE INDEX IF NOT EXISTS idx_tm_global ON translation_memory(is_global) WHERE is_global = 1;

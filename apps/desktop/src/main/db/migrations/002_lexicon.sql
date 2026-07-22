-- v3 (2026-07-22) — Lexique (glossaire) + aliases.
-- Consolidé depuis 001_initial (lexicon) + 003_lexicon_metadata + 005_alias_export_prompts_stats.

CREATE TABLE IF NOT EXISTS lexicon (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  translation TEXT NOT NULL,
  category TEXT NOT NULL,
  aliases TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  forbidden TEXT,
  priority INTEGER NOT NULL DEFAULT 0,
  description TEXT,
  notes TEXT,
  metadata TEXT
);

-- SDD §6.3 : aliases dans une table séparée (relation 1-N).
CREATE TABLE IF NOT EXISTS lexicon_aliases (
  id TEXT PRIMARY KEY,
  lexicon_id TEXT NOT NULL REFERENCES lexicon(id) ON DELETE CASCADE,
  alias TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lexicon_project ON lexicon(project_id);
CREATE INDEX IF NOT EXISTS idx_lexicon_aliases_lexicon ON lexicon_aliases(lexicon_id);

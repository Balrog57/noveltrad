-- 005_alias_export_prompts_stats : Tables SDD §6.2-6.3

-- SDD §6.3 : table séparée pour les aliases du lexique
CREATE TABLE IF NOT EXISTS lexicon_aliases (
  id TEXT PRIMARY KEY,
  lexicon_id TEXT NOT NULL REFERENCES lexicon(id) ON DELETE CASCADE,
  alias TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lexicon_aliases_lexicon ON lexicon_aliases(lexicon_id);

-- SDD §6.2 : table exports (traçage des exports)
CREATE TABLE IF NOT EXISTS exports (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT,
  format TEXT NOT NULL,
  output_path TEXT NOT NULL,
  file_size INTEGER,
  bilingual INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

-- SDD §6.2 : table prompts (templates versionnés)
CREATE TABLE IF NOT EXISTS prompts (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  version TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'system',
  language TEXT NOT NULL DEFAULT 'fr',
  target_model TEXT,
  output_format TEXT NOT NULL DEFAULT 'text',
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- SDD §6.2 : table statistics (métriques agrégées)
CREATE TABLE IF NOT EXISTS statistics (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  metric TEXT NOT NULL,
  value REAL NOT NULL,
  recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_statistics_project ON statistics(project_id);

CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  stage TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  config_schema TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
  type TEXT NOT NULL DEFAULT 'single',
  status TEXT NOT NULL DEFAULT 'pending',
  started_at TEXT,
  finished_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_steps (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  agent_id TEXT NOT NULL,
  name TEXT NOT NULL,
  stage TEXT NOT NULL,
  order_index INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  input_snapshot TEXT,
  output_snapshot TEXT,
  score REAL,
  tokens_in INTEGER,
  tokens_out INTEGER,
  duration_ms INTEGER,
  started_at TEXT,
  finished_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS history_snapshots (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
  job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
  step_id TEXT REFERENCES job_steps(id) ON DELETE SET NULL,
  stage TEXT NOT NULL,
  paragraphs TEXT NOT NULL,
  metadata TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_job_steps_job ON job_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_history_chapter ON history_snapshots(chapter_id);

-- Seed native agents
INSERT OR IGNORE INTO agents (id, name, stage, enabled, config_schema, created_at) VALUES
('split', 'Decoupage', 'split', 1, '{"maxParagraphLength": {"type": "integer"}}', datetime('now')),
('pre_translate', 'Pre-traduction', 'pre_translate', 1, '{"model": {"type": "string"}}', datetime('now')),
('translate', 'Traduction IA', 'translate', 1, '{"model": {"type": "string"}}', datetime('now')),
('consistency', 'Coherence', 'consistency', 1, '{}', datetime('now')),
('lexicon', 'Lexique', 'lexicon', 1, '{}', datetime('now')),
('grammar', 'Grammaire', 'grammar', 1, '{"language": {"type": "string"}}', datetime('now')),
('style', 'Style', 'style', 1, '{"tone": {"type": "string"}}', datetime('now')),
('polish', 'Polish', 'polish', 1, '{}', datetime('now')),
('qa', 'QA', 'qa', 1, '{}', datetime('now')),
('export', 'Export', 'export', 1, '{"format": {"type": "string"}}', datetime('now'));

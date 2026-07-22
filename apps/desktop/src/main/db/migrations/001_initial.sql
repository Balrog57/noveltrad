-- v3 (2026-07-22) — Schéma consolidé.
-- Remplace les anciennes migrations 001-018 (pre-v3). Greenfield : aucun
-- utilisateur à migrer. Seules les tables réellement utilisées par le pipeline
-- v3 (SimpleWorkflowRunner 4-stages) sont conservées.
--
-- Tables conservées : projects, chapters, paragraphs, settings.
-- (lexicon, translation_memory, summaries, prompts dans les migrations suivantes.)
--
-- Tables supprimées (plus référencées en v3) : jobs, job_steps, agents,
-- history_snapshots, audit_log, embeddings, exports, statistics,
-- model_calibrations, review_reports, models.

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  author TEXT,
  source_language TEXT NOT NULL,
  target_language TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT,
  source_path TEXT,
  order_index INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  metadata TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paragraphs (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  index_in_chapter INTEGER NOT NULL,
  source_text TEXT NOT NULL,
  translated_text TEXT,
  pre_translated_text TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  metadata TEXT
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_paragraphs_chapter ON paragraphs(chapter_id);

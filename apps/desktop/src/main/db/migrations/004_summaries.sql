-- v3 (2026-07-22) — Summaries (Summarizer transverse).
-- Consolidé depuis 015_summaries. Cohérence cross-chapitre : le résumé du roman
-- est injecté dans le contexte des stages translate/proofread/validate.

CREATE TABLE IF NOT EXISTS chapter_summaries (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  summary TEXT NOT NULL,
  token_count INTEGER,
  created_at TEXT NOT NULL,
  UNIQUE(chapter_id)
);

CREATE TABLE IF NOT EXISTS novel_summaries (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
  summary TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chapter_summaries_project ON chapter_summaries(project_id);
CREATE INDEX IF NOT EXISTS idx_chapter_summaries_chapter ON chapter_summaries(chapter_id);

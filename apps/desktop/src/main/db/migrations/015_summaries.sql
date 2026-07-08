-- 015_summaries : Summarizer transverse v1.4 (SDD §7.13, §8.12)
--
-- Persiste les résumés produits par le SummarizerAgent pour la cohérence
-- cross-chapitre (noms, intrigue, ton) sur l'ensemble d'un roman.
--
-- Inspiration : LaTeXTrans (Summarizer), TransAgents.
-- Le NovelSummary est injecté dans le contexte de translate/style/polish
-- des chapitres suivants → évite la dérive des noms sur 500 chapitres.

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

-- Enregistrement du Summarizer dans le registre (idempotent).
INSERT OR IGNORE INTO agents (id, name, stage, enabled, config_schema) VALUES
  ('summarizer', 'Resume', 'summarizer', 1, '{}');

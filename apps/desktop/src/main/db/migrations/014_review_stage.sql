-- 014_review_stage : Boucle de révision pro v1.4 (SDD §7.12, §8.10-8.11)
--
-- Persiste le ReviewReport produit par le ReviewAgent, consommé par le
-- ReviseAgent et exposé dans l'UI pour édition/acceptation humaine.
--
-- Inspiration : honya (Reviewer), LaTeXTrans (Validator).
-- Le ReviewReport contient des corrections ciblées paragraphe-par-paragraphe
-- (issues[]: paragraphIndex, severity, category, original, suggestion, reason).

CREATE TABLE IF NOT EXISTS review_reports (
  id TEXT PRIMARY KEY,
  job_step_id TEXT NOT NULL REFERENCES job_steps(id) ON DELETE CASCADE,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
  issues TEXT NOT NULL,        -- JSON: ReviewIssue[]
  summary TEXT NOT NULL,       -- synthèse globale du réviseur
  status TEXT NOT NULL DEFAULT 'pending',  -- pending | accepted | rejected | edited
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_review_reports_job ON review_reports(job_id);
CREATE INDEX IF NOT EXISTS idx_review_reports_chapter ON review_reports(chapter_id);
CREATE INDEX IF NOT EXISTS idx_review_reports_project ON review_reports(project_id);

-- Enregistrement des 2 nouveaux agents dans le registre (idempotent).
-- On utilise INSERT OR IGNORE pour ne pas écraser une config existante.
INSERT OR IGNORE INTO agents (id, name, stage, enabled, config_schema) VALUES
  ('review', 'Réviseur', 'review', 1, '{}'),
  ('revise', 'Correcteur', 'revise', 1, '{}');

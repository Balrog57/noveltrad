-- 008_audit : Journal d'audit des actions utilisateur (SDD §14.6)
-- Trace les actions importantes : création de projet, import de chapitre,
-- démarrage de workflow, export, rollback, snapshot manuel, etc.
-- Chaque entrée enregistre l'action, le type d'entité concernée,
-- et des détails contextuels au format JSON.

CREATE TABLE IF NOT EXISTS audit_log (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  entity_type TEXT,
  entity_id TEXT,
  details TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_log(project_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

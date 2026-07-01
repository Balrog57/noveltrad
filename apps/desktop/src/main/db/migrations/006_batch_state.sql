-- 006_batch_state : Persistance de l'état des jobs batch (SDD §7.11)
-- Permet la reprise après interruption (crash / fermeture app) au dernier chapitre non terminé.

-- Colonne chapter_ids : liste des chapitres du batch (JSON array)
ALTER TABLE jobs ADD COLUMN chapter_ids TEXT;

-- Colonne metadata : métadonnées du job (JSON object) — inclut batchChapterIndex pour la reprise
ALTER TABLE jobs ADD COLUMN metadata TEXT;

-- Index pour retrouver rapidement les jobs en cours (running/paused) à recharger au démarrage
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
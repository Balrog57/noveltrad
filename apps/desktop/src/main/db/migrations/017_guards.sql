-- 017_guards : Guards anti-boucle (retries QA par chapitre)
--
-- Compteur de retries QA automatiques déclenchés par un score intermédiaire
-- (WorkflowEngine.runStep, branche "score >= threshold - 20"). Permet de borner
-- le nombre de retryWeakestStep() par chapitre via le setting maxQaRetries
-- (défaut 3) : au-delà, le workflow est mis en pause pour review humaine plutôt
-- que de boucler indéfiniment sur la passe QA.
--
-- Colonne dédiée (plutôt que metadata JSON) : lisible et filtrable directement
-- en SQL (WHERE qa_retry_count >= max), cohérente avec cost_usd (migration 013).

ALTER TABLE jobs ADD COLUMN qa_retry_count INTEGER NOT NULL DEFAULT 0;

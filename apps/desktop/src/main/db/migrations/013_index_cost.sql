-- 013_index_cost : Indexes de couverture + colonne cost_usd (SDD §3.8, §6.4, audit G3/G5)
--
-- Deux indexes manquants identifiés par l'audit SDD (2026-07-07) :
--   * idx_paragraphs_status : filtre des paragraphes par statut dans l'éditeur
--     chapitres (requêtes fréquentes sur paragraphs WHERE status = 'pending').
--   * idx_prompts_agent : recherche des prompts par agent dans PromptLoader
--     (WHERE agent_id = ? ORDER BY version DESC).
--
-- Colonne cost_usd sur jobs (SDD §3.8) :
--   Accumulation du coût estimé d'un job (providers cloud facturant au token).
--   Nulle pour les modèles locaux (Ollama). Mise à jour par WorkflowEngine
--   après chaque étape via AiRouter.estimateCost().

ALTER TABLE jobs ADD COLUMN cost_usd REAL;
CREATE INDEX IF NOT EXISTS idx_paragraphs_status ON paragraphs(status);
CREATE INDEX IF NOT EXISTS idx_prompts_agent ON prompts(agent_id);

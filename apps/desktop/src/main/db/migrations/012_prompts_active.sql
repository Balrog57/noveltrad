-- 012_prompts_active : Colonne active pour overrides de prompts (SDD §25, T5)
--
-- PromptLoader.load() query `WHERE active = 1` pour résoudre les overrides
-- runtime. Avant cette migration, la colonne `active` n'existait pas dans la
-- table `prompts` (migration 005) → toute query DB throw → fallback
-- silencieux permanent sur les constantes TS → override DB non fonctionnel.
--
-- Ajoute la colonne `active` (défaut 1 = actif) + index composite pour
-- accélérer la résolution (id, active, version).

ALTER TABLE prompts ADD COLUMN active INTEGER NOT NULL DEFAULT 1;
CREATE INDEX IF NOT EXISTS idx_prompts_id_active_version ON prompts(id, active, version);

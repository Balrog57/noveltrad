-- v3 (2026-07-22) — Prompts (override DB optionnel).
-- Consolidé depuis 005_alias_export_prompts_stats (table prompts) +
-- 012_prompts_active. Permet à l'utilisateur d'overrider les system prompts
-- des 4 stages v3 (translate, proofread, glossary, validate) via PromptLoader.
-- Si la table est vide/absente, le fallback TS s'applique (comportement par défaut).

CREATE TABLE IF NOT EXISTS prompts (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  version TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'system',
  language TEXT NOT NULL DEFAULT 'fr',
  target_model TEXT,
  output_format TEXT NOT NULL DEFAULT 'text',
  content TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

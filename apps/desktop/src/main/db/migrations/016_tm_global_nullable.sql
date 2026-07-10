-- Bug fix : promoteToGlobal() dans TranslationMemoryEngine insérait project_id = NULL
-- mais le schéma 001_initial.sql déclare `project_id TEXT NOT NULL` → violation
-- systématique de la contrainte NOT NULL. Code dormant (jamais appelé en prod),
-- mais cassé si quelqu'un l'invoque.
--
-- SQLite ne supporte pas ALTER COLUMN pour modifier NOT NULL → on recrée
-- la table avec le pattern standard :
--   1. Créer nouvelle table avec le schéma corrigé
--   2. Copier les données
--   3. Drop ancienne table
--   4. Renommer nouvelle table
--   5. Recréer les index
--
-- Le FK project_id est passé de NOT NULL + ON DELETE CASCADE à nullable +
-- ON DELETE SET NULL (les entrées globales ne doivent pas être supprimées
-- en cascade quand un projet est supprimé).

CREATE TABLE IF NOT EXISTS translation_memory_new (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
  source_text TEXT NOT NULL,
  target_text TEXT NOT NULL,
  source_language TEXT NOT NULL,
  target_language TEXT NOT NULL,
  usage_count INTEGER NOT NULL DEFAULT 1,
  last_used_at TEXT,
  created_at TEXT NOT NULL,
  normalized_hash TEXT,
  segment_index INTEGER DEFAULT 0,
  is_global INTEGER DEFAULT 0
);

INSERT OR IGNORE INTO translation_memory_new
  (id, project_id, source_text, target_text, source_language, target_language,
   usage_count, last_used_at, created_at, normalized_hash, segment_index, is_global)
SELECT id, project_id, source_text, target_text, source_language, target_language,
   usage_count, last_used_at, created_at, normalized_hash, segment_index, is_global
FROM translation_memory;

DROP TABLE translation_memory;

ALTER TABLE translation_memory_new RENAME TO translation_memory;

CREATE INDEX IF NOT EXISTS idx_tm_project_text ON translation_memory(project_id, source_text);
CREATE INDEX IF NOT EXISTS idx_tm_normalized ON translation_memory(normalized_hash);
CREATE INDEX IF NOT EXISTS idx_tm_global ON translation_memory(is_global) WHERE is_global = 1;

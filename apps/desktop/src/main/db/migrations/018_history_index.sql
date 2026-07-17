-- 018_history_index.sql
-- Workstream A (refactor) : index composite manquant sur history_snapshots.
--
-- Contexte : HistoryRepository.getLastFullSnapshot et listByProject filtrent
-- par (project_id [, chapter_id]) avec un ORDER BY created_at. L'index existant
-- `idx_history_chapter` ne couvre que chapter_id → full scan sur project_id,
-- de plus en plus lent à mesure que l'historique grossit ( getLastFullSnapshot
-- est appelé à CHAQUE création de snapshot incrémental).
--
-- Cet index composite couvre les deux axes de recherche et le tri.
CREATE INDEX IF NOT EXISTS idx_history_project_chapter_created
  ON history_snapshots (project_id, chapter_id, created_at DESC);

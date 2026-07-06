-- T13: RAG vector search enhancements
-- Approche retenue: préfiltre MiniSearch + cosinus JS (cache par projet) + seuil.
-- SDD §9.3 ne requiert aucune lib vectorielle native; sqlite-vec abandonné
-- (POC KO sur node-sqlite3-wasm, pas de loadExtension). Conforme jusqu'à ~10k paragraphes.
-- Index pour accélérer les queries findSimilar au niveau projet.
CREATE INDEX IF NOT EXISTS idx_emb_project_para ON embeddings(chapter_id, paragraph_id);

-- T13: RAG vector search enhancements
-- sqlite-vec not compatible with node-sqlite3-wasm (no loadExtension).
-- Fallback: brute-force + MiniSearch prefilter + cosine threshold.
-- Index for faster project-level queries in findSimilar.
CREATE INDEX IF NOT EXISTS idx_emb_project_para ON embeddings(chapter_id, paragraph_id);

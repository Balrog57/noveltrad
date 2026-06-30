CREATE TABLE IF NOT EXISTS embeddings (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  paragraph_id TEXT NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
  embedding_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_embeddings_chapter ON embeddings(chapter_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_paragraph ON embeddings(paragraph_id);

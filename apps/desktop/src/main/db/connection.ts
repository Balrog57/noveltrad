import sqlite3 from "node-sqlite3-wasm";
import type { Database } from "node-sqlite3-wasm";
import path from "node:path";
import fs from "node:fs";

export type ProjectDatabase = Database;

const MIGRATIONS = [
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  author TEXT,
  source_language TEXT NOT NULL,
  target_language TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE TABLE IF NOT EXISTS chapters (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT,
  source_path TEXT,
  order_index INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE TABLE IF NOT EXISTS paragraphs (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  index_in_chapter INTEGER NOT NULL,
  source_text TEXT NOT NULL,
  translated_text TEXT,
  pre_translated_text TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  metadata TEXT
)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE TABLE IF NOT EXISTS lexicon (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  translation TEXT NOT NULL,
  category TEXT NOT NULL,
  aliases TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  forbidden TEXT,
  priority INTEGER NOT NULL DEFAULT 0,
  description TEXT,
  notes TEXT
)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE TABLE IF NOT EXISTS translation_memory (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_text TEXT NOT NULL,
  target_text TEXT NOT NULL,
  source_language TEXT NOT NULL,
  target_language TEXT NOT NULL,
  usage_count INTEGER NOT NULL DEFAULT 1,
  last_used_at TEXT,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE TABLE IF NOT EXISTS models (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  name TEXT NOT NULL,
  model TEXT NOT NULL,
  host TEXT,
  api_key TEXT,
  is_default INTEGER NOT NULL DEFAULT 0,
  is_fallback INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE INDEX IF NOT EXISTS idx_paragraphs_chapter ON paragraphs(chapter_id)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE INDEX IF NOT EXISTS idx_lexicon_project ON lexicon(project_id)`,
  },
  {
    version: 1,
    name: "001_initial",
    sql: `CREATE INDEX IF NOT EXISTS idx_tm_project_text ON translation_memory(project_id, source_text)`,
  },
  {
    version: 2,
    name: "002_jobs",
    sql: `CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  stage TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  config_schema TEXT,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 2,
    name: "002_jobs",
    sql: `CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
  type TEXT NOT NULL DEFAULT 'single',
  status TEXT NOT NULL DEFAULT 'pending',
  started_at TEXT,
  finished_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 2,
    name: "002_jobs",
    sql: `CREATE TABLE IF NOT EXISTS job_steps (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  agent_id TEXT NOT NULL,
  name TEXT NOT NULL,
  stage TEXT NOT NULL,
  order_index INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  input_snapshot TEXT,
  output_snapshot TEXT,
  score REAL,
  tokens_in INTEGER,
  tokens_out INTEGER,
  duration_ms INTEGER,
  started_at TEXT,
  finished_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 2,
    name: "002_jobs",
    sql: `CREATE TABLE IF NOT EXISTS history_snapshots (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
  job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
  step_id TEXT REFERENCES job_steps(id) ON DELETE SET NULL,
  stage TEXT NOT NULL,
  paragraphs TEXT NOT NULL,
  metadata TEXT,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 2,
    name: "002_jobs",
    sql: `CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id)`,
  },
  {
    version: 2,
    name: "002_jobs",
    sql: `CREATE INDEX IF NOT EXISTS idx_job_steps_job ON job_steps(job_id)`,
  },
  {
    version: 2,
    name: "002_jobs",
    sql: `CREATE INDEX IF NOT EXISTS idx_history_chapter ON history_snapshots(chapter_id)`,
  },
  {
    version: 2,
    name: "002_jobs",
    sql: `INSERT OR IGNORE INTO agents (id, name, stage, enabled, config_schema, created_at) VALUES
('split', 'Decoupage', 'split', 1, '{"maxParagraphLength": {"type": "integer"}}', datetime('now')),
('pre_translate', 'Pre-traduction', 'pre_translate', 1, '{"model": {"type": "string"}}', datetime('now')),
('translate', 'Traduction IA', 'translate', 1, '{"model": {"type": "string"}}', datetime('now')),
('consistency', 'Coherence', 'consistency', 1, '{}', datetime('now')),
('lexicon', 'Lexique', 'lexicon', 1, '{}', datetime('now')),
('grammar', 'Grammaire', 'grammar', 1, '{"language": {"type": "string"}}', datetime('now')),
('style', 'Style', 'style', 1, '{"tone": {"type": "string"}}', datetime('now')),
('polish', 'Polish', 'polish', 1, '{}', datetime('now')),
('qa', 'QA', 'qa', 1, '{}', datetime('now')),
('export', 'Export', 'export', 1, '{"format": {"type": "string"}}', datetime('now'))`,
  },
  {
    version: 3,
    name: "003_lexicon_metadata",
    sql: `ALTER TABLE lexicon ADD COLUMN metadata TEXT`,
  },
  {
    version: 4,
    name: "004_rag",
    sql: `CREATE TABLE IF NOT EXISTS embeddings (
  id TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  paragraph_id TEXT NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
  embedding_json TEXT NOT NULL,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 4,
    name: "004_rag",
    sql: `CREATE INDEX IF NOT EXISTS idx_embeddings_chapter ON embeddings(chapter_id)`,
  },
  {
    version: 4,
    name: "004_rag",
    sql: `CREATE INDEX IF NOT EXISTS idx_embeddings_paragraph ON embeddings(paragraph_id)`,
  },
  {
    version: 5,
    name: "005_alias_export_prompts_stats",
    sql: `CREATE TABLE IF NOT EXISTS lexicon_aliases (
  id TEXT PRIMARY KEY,
  lexicon_id TEXT NOT NULL REFERENCES lexicon(id) ON DELETE CASCADE,
  alias TEXT NOT NULL
)`,
  },
  {
    version: 5,
    name: "005_alias_export_prompts_stats",
    sql: `CREATE INDEX IF NOT EXISTS idx_lexicon_aliases_lexicon ON lexicon_aliases(lexicon_id)`,
  },
  {
    version: 5,
    name: "005_alias_export_prompts_stats",
    sql: `CREATE TABLE IF NOT EXISTS exports (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chapter_id TEXT,
  format TEXT NOT NULL,
  output_path TEXT NOT NULL,
  file_size INTEGER,
  bilingual INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 5,
    name: "005_alias_export_prompts_stats",
    sql: `CREATE TABLE IF NOT EXISTS prompts (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  version TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'system',
  language TEXT NOT NULL DEFAULT 'fr',
  target_model TEXT,
  output_format TEXT NOT NULL DEFAULT 'text',
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
)`,
  },
  {
    version: 5,
    name: "005_alias_export_prompts_stats",
    sql: `CREATE TABLE IF NOT EXISTS statistics (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  metric TEXT NOT NULL,
  value REAL NOT NULL,
  recorded_at TEXT NOT NULL
)`,
  },
  {
    version: 5,
    name: "005_alias_export_prompts_stats",
    sql: `CREATE INDEX IF NOT EXISTS idx_statistics_project ON statistics(project_id)`,
  },
];

export function createProjectDatabase(projectPath: string): Database {
  if (!fs.existsSync(projectPath)) {
    throw new Error(`Dossier projet introuvable : ${projectPath}`);
  }
  const dbPath = path.join(projectPath, "project.db");
  const db = new sqlite3.Database(dbPath);
  db.exec("PRAGMA journal_mode = WAL");
  db.exec("PRAGMA foreign_keys = ON");
  return db;
}

export function runMigrations(db: Database, migrationsDir?: string): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS __migrations (
      version INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      applied_at TEXT NOT NULL
    )
  `);

  const applied = new Set(
    (db.prepare("SELECT version FROM __migrations").all() as { version: number }[]).map(
      (r) => r.version,
    ),
  );

  const recorded = new Map<number, string>();
  for (const m of MIGRATIONS) {
    if (applied.has(m.version)) continue;
    if (!recorded.has(m.version)) {
      recorded.set(m.version, m.name);
    }
    db.exec(m.sql);
  }

  const now = new Date().toISOString();
  for (const [version, name] of recorded) {
    db.prepare(
      "INSERT INTO __migrations (version, name, applied_at) VALUES (?, ?, ?)",
    ).run([version, name, now]);
  }

  if (migrationsDir && fs.existsSync(migrationsDir)) {
    const files = fs
      .readdirSync(migrationsDir)
      .filter((f) => f.endsWith(".sql"))
      .sort();

    for (const file of files) {
      const version = parseInt(file.split("_")[0], 10);
      if (applied.has(version) || recorded.has(version)) continue;

      const appliedRow = db
        .prepare("SELECT 1 FROM __migrations WHERE version = ?")
        .get([version]);
      if (appliedRow) continue;

      const sql = fs.readFileSync(path.join(migrationsDir, file), "utf-8");
      db.exec(sql);
      db.prepare(
        "INSERT INTO __migrations (version, name, applied_at) VALUES (?, ?, ?)",
      ).run([version, file, now]);
    }
  }
}

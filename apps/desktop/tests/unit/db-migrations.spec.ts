import { describe, it, expect, beforeEach, afterEach } from "vitest";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";
import sqlite3 from "node-sqlite3-wasm";
import { runMigrations } from "../../src/main/db/connection";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Crée un dossier temporaire avec des fichiers de migration .sql. */
function createTempDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "db-migrations-test-"));
}

/** Écrit un fichier .sql de migration dans le dossier. */
function writeMigration(dir: string, name: string, sql: string): void {
  fs.writeFileSync(path.join(dir, name), sql, "utf-8");
}

/** Exécute du SQL brut sur une DB. */
function execSql(db: sqlite3.Database, sql: string): void {
  db.exec(sql);
}

/** Récupère toutes les entrées de __migrations triées par version. */
function getMigrations(
  db: sqlite3.Database,
): { version: number; name: string; applied_at: string }[] {
  return db
    .prepare("SELECT version, name, applied_at FROM __migrations ORDER BY version")
    .all() as { version: number; name: string; applied_at: string }[];
}

/** Vérifie si une colonne existe dans une table. */
function columnExists(
  db: sqlite3.Database,
  table: string,
  column: string,
): boolean {
  const cols = db
    .prepare(`PRAGMA table_info(${table})`)
    .all() as { name: string }[];
  return cols.some((c) => c.name === column);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("runMigrations — file-based unified runner (T2)", () => {
  let db: sqlite3.Database;
  let tempDir: string;

  beforeEach(() => {
    db = new sqlite3.Database();
    tempDir = createTempDir();
  });

  afterEach(() => {
    if (db) db.close();
    if (tempDir && fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // ── Test 1 : DB fraîche → toutes les migrations s'exécutent ──
  it("fresh DB executes all migrations (v1–v12) and chapters.metadata exists", () => {
    // Copier les fichiers de migration réels dans le dossier temporaire
    const realMigrationsDir = path.resolve(
      __dirname,
      "../../src/main/db/migrations",
    );
    const files = fs
      .readdirSync(realMigrationsDir)
      .filter((f) => f.endsWith(".sql"))
      .sort();
    for (const f of files) {
      const sql = fs.readFileSync(path.join(realMigrationsDir, f), "utf-8");
      writeMigration(tempDir, f, sql);
    }

    runMigrations(db, tempDir);

    const rows = getMigrations(db);
    expect(rows.length).toBe(12);
    expect(rows[0].version).toBe(1);
    expect(rows[11].version).toBe(12);
    expect(rows[11].name).toBe("012_prompts_active.sql");

    // Vérifier que la colonne metadata a été ajoutée à chapters
    expect(columnExists(db, "chapters", "metadata")).toBe(true);
    // T5 fix : la colonne active a été ajoutée à prompts
    expect(columnExists(db, "prompts", "active")).toBe(true);
  });

  // ── Test 2 : DB existante v1-v8 → seules v9-v11 s'exécutent ──
  it("existing DB with v1–v8 only runs v9, v10 and v11", () => {
    // Simuler une DB existante du système inline : créer les tables v1-v8
    // et laisser __migrations vide (comme le faisait l'ancien système)
    execSql(
      db,
      `CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, author TEXT,
        source_language TEXT NOT NULL, target_language TEXT NOT NULL,
        path TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      )`,
    );
    execSql(
      db,
      `CREATE TABLE IF NOT EXISTS chapters (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        title TEXT, source_path TEXT, order_index INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      )`,
    );
    execSql(
      db,
      `CREATE TABLE IF NOT EXISTS paragraphs (
        id TEXT PRIMARY KEY, chapter_id TEXT NOT NULL, index_in_chapter INTEGER NOT NULL,
        source_text TEXT NOT NULL, translated_text TEXT, pre_translated_text TEXT,
        status TEXT NOT NULL DEFAULT 'pending', metadata TEXT
      )`,
    );
    // La migration v1 crée aussi translation_memory (nécessaire pour v10 ALTER TABLE)
    execSql(
      db,
      `CREATE TABLE IF NOT EXISTS translation_memory (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        source_text TEXT NOT NULL, target_text TEXT NOT NULL,
        source_language TEXT NOT NULL, target_language TEXT NOT NULL,
        usage_count INTEGER NOT NULL DEFAULT 1,
        last_used_at TEXT, created_at TEXT NOT NULL
      )`,
    );
    // La migration v4 crée embeddings (nécessaire pour v11)
    execSql(
      db,
      `CREATE TABLE IF NOT EXISTS embeddings (
        id TEXT PRIMARY KEY, chapter_id TEXT NOT NULL, paragraph_id TEXT NOT NULL,
        embedding_json TEXT NOT NULL, created_at TEXT NOT NULL
      )`,
    );

    // Créer les fichiers dans le dossier temporaire
    writeMigration(
      tempDir,
      "001_initial.sql",
      "CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL)",
    );
    writeMigration(
      tempDir,
      "002_jobs.sql",
      "CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, name TEXT NOT NULL)",
    );
    writeMigration(tempDir, "009_chapter_metadata.sql", "ALTER TABLE chapters ADD COLUMN metadata TEXT");
    writeMigration(tempDir, "010_tm_enhancements.sql", "ALTER TABLE translation_memory ADD COLUMN normalized_hash TEXT");
    writeMigration(tempDir, "011_rag_vectors.sql", "CREATE INDEX IF NOT EXISTS idx_test ON embeddings(paragraph_id)");

    runMigrations(db, tempDir);

    const rows = getMigrations(db);
    // La détection héritage marque v1-v8 comme appliquées (8 entrées legacy),
    // seules v9 et v10 sont réellement exécutées via les fichiers
    expect(rows.length).toBe(11);
    expect(rows[0].version).toBe(1);
    expect(rows[7].version).toBe(8);
    expect(rows[8].version).toBe(9);
    expect(rows[8].name).toBe("009_chapter_metadata.sql");
    expect(rows[9].version).toBe(10);
    expect(rows[9].name).toBe("010_tm_enhancements.sql");
    expect(rows[10].version).toBe(11);
    expect(rows[10].name).toBe("011_rag_vectors.sql");
    expect(columnExists(db, "chapters", "metadata")).toBe(true);
  });

  // ── Test 3 : Fichier SQL invalide → rollback + erreur ──
  it("invalid SQL rolls back the failed migration and throws", () => {
    writeMigration(tempDir, "001_initial.sql", "CREATE TABLE test (id TEXT PRIMARY KEY)");
    writeMigration(tempDir, "002_broken.sql", "INVALID SQL STATEMENT !!!");
    writeMigration(tempDir, "003_after.sql", "CREATE TABLE after_broken (id TEXT PRIMARY KEY)");

    expect(() => runMigrations(db, tempDir)).toThrow();

    // v1 doit être appliquée (commitée avant la tentative v2)
    // v2 ne doit PAS être dans __migrations
    // v3 ne doit PAS être dans __migrations
    const rows = getMigrations(db);
    expect(rows.length).toBe(1);
    expect(rows[0].version).toBe(1);

    // v2 ne doit laisser aucune trace (table test ne doit pas exister non plus… on vérifie juste la migration)
    // Note: la table test a été créée par v1
    const tables = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='after_broken'",
      )
      .all() as { name: string }[];
    expect(tables.length).toBe(0);
  });

  // ── Test 4 : Numéros en désordre → tri correct ──
  it("sorts files by numeric prefix regardless of write order", () => {
    writeMigration(tempDir, "003_last.sql", "CREATE TABLE third_migration (id TEXT PRIMARY KEY)");
    writeMigration(tempDir, "001_first.sql", "CREATE TABLE first_migration (id TEXT PRIMARY KEY)");
    writeMigration(tempDir, "002_second.sql", "CREATE TABLE second_migration (id TEXT PRIMARY KEY)");

    runMigrations(db, tempDir);

    const rows = getMigrations(db);
    expect(rows.length).toBe(3);
    expect(rows[0].version).toBe(1);
    expect(rows[1].version).toBe(2);
    expect(rows[2].version).toBe(3);

    // Vérifier que les tables ont bien été créées dans l'ordre
    const tables = db
      .prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_migration' ORDER BY name",
      )
      .all() as { name: string }[];
    expect(tables.some((t) => t.name === "first_migration")).toBe(true);
    expect(tables.some((t) => t.name === "second_migration")).toBe(true);
    expect(tables.some((t) => t.name === "third_migration")).toBe(true);
  });

  // ── Test 5 : Fichier sans préfixe numérique → ignoré ──
  it("ignores .sql files without a numeric prefix", () => {
    writeMigration(tempDir, "001_valid.sql", "CREATE TABLE valid_table (id TEXT PRIMARY KEY)");
    writeMigration(tempDir, "setup.sql", "CREATE TABLE setup_table (id TEXT PRIMARY KEY)");
    writeMigration(tempDir, "migration_helpers.sql", "CREATE TABLE helpers (id TEXT PRIMARY KEY)");

    runMigrations(db, tempDir);

    const rows = getMigrations(db);
    expect(rows.length).toBe(1);
    expect(rows[0].version).toBe(1);
    expect(rows[0].name).toBe("001_valid.sql");

    // Seule valid_table doit exister
    const tables = db
      .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('__migrations', 'sqlite_sequence')")
      .all() as { name: string }[];
    expect(tables.length).toBe(1);
    expect(tables[0].name).toBe("valid_table");
  });
});

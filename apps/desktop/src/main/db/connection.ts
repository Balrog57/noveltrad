import { Database } from "node-sqlite3-wasm";
import path from "node:path";
import fs from "node:fs";

export type ProjectDatabase = Database;

export function createProjectDatabase(projectPath: string): Database {
  const dbPath = path.join(projectPath, "project.db");
  const db = new Database(dbPath);
  db.exec("PRAGMA journal_mode = WAL");
  db.exec("PRAGMA foreign_keys = ON");
  return db;
}

export function runMigrations(db: Database, migrationsDir: string): void {
  const files = fs
    .readdirSync(migrationsDir)
    .filter((f) => f.endsWith(".sql"))
    .sort();
  db.exec(`
    CREATE TABLE IF NOT EXISTS __migrations (
      version INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      applied_at TEXT NOT NULL
    )
  `);

  for (const file of files) {
    const version = parseInt(file.split("_")[0], 10);
    const applied = db
      .prepare("SELECT 1 FROM __migrations WHERE version = ?")
      .get([version]);
    if (applied) continue;

    const sql = fs.readFileSync(path.join(migrationsDir, file), "utf-8");
    db.exec(sql);
    db.prepare(
      "INSERT INTO __migrations (version, name, applied_at) VALUES (?, ?, ?)",
    ).run([version, file, new Date().toISOString()]);
  }
}

import sqlite3 from "node-sqlite3-wasm";
import type { Database } from "node-sqlite3-wasm";
import path from "node:path";
import fs from "node:fs";
import { MIGRATIONS } from "./migrationsManifest.js";

export type ProjectDatabase = Database;

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

/** Internal: versions devant être marquées comme appliquées quand on détecte une DB existante du système inline (pre-v9). */
const LEGACY_VERSIONS = [
  { version: 1, name: "001_initial.sql" },
  { version: 2, name: "002_jobs.sql" },
  { version: 3, name: "003_lexicon_metadata.sql" },
  { version: 4, name: "004_rag.sql" },
  { version: 5, name: "005_alias_export_prompts_stats.sql" },
  { version: 6, name: "006_batch_state.sql" },
  { version: 7, name: "007_quality.sql" },
  { version: 8, name: "008_audit.sql" },
] as const;

export function runMigrations(db: Database, migrationsDir?: string): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS __migrations (
      version INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      applied_at TEXT NOT NULL
    )
  `);

  const applied = new Set<number>();
  for (const row of db.prepare("SELECT version FROM __migrations").all() as {
    version: number;
  }[]) {
    applied.add(row.version);
  }

  // Migration depuis l'ancien système inline (pre-v9) : si la base a des tables
  // utilisateur mais que __migrations est vide, on marque v1-v8 comme appliquées.
  if (applied.size === 0) {
    const tables = db
      .prepare(
        "SELECT count(*) as cnt FROM sqlite_master WHERE type='table' AND name NOT IN ('__migrations', 'sqlite_sequence')",
      )
      .all() as { cnt: number }[];
    if (tables.length > 0 && tables[0].cnt > 0) {
      const now = new Date().toISOString();
      const stmt = db.prepare(
        "INSERT OR IGNORE INTO __migrations (version, name, applied_at) VALUES (?, ?, ?)",
      );
      for (const lv of LEGACY_VERSIONS) {
        stmt.run([lv.version, lv.name, now]);
        applied.add(lv.version);
      }
    }
  }

  // Source des migrations : soit un dossier explicite (tests), soit le
  // manifest bundled (prod — voir migrationsManifest.ts). On ne silencie plus
  // l'absence de migrations : c'est précisément ce qui masquait le vrai bug
  // "no such table: projects" (le dossier n'était pas embarqué dans le build).
  let pending: { version: number; name: string; sql: string }[];
  if (migrationsDir) {
    if (!fs.existsSync(migrationsDir)) {
      throw new Error(
        `Dossier de migrations introuvable : ${migrationsDir}`,
      );
    }
    const files = fs
      .readdirSync(migrationsDir)
      .filter((f) => f.endsWith(".sql") && /^\d+/.test(f))
      .sort();
    pending = files.map((file) => {
      const match = file.match(/^(\d+)/);
      const version = match ? parseInt(match[1], 10) : NaN;
      const sql = fs.readFileSync(path.join(migrationsDir, file), "utf-8");
      return { version, name: file, sql };
    });
  } else {
    pending = MIGRATIONS;
  }

  if (pending.length === 0) {
    // Échec bruyant : éviter de créer une base sans schéma puis de planter
    // plus loin avec une erreur trompeuse (ex: "no such table").
    throw new Error(
      "Aucune migration à appliquer : vérifier le bundle migrationsManifest / le migrationsDir.",
    );
  }

  for (const { version, name: file, sql } of pending) {
    if (Number.isNaN(version)) continue;
    if (applied.has(version)) continue;

    // T4B fix : robustesse transactionnelle. Si le SQL de migration contient
    // déjà sa propre transaction (BEGIN/COMMIT/START TRANSACTION), on ne
    // wrapper pas — SQLite ne supporte pas les transactions imbriquées via
    // exec() brut et lèverait "cannot start a transaction within a transaction".
    const hasOwnTransaction = /\b(BEGIN|START\s+TRANSACTION|COMMIT)\b/i.test(sql);

    try {
      if (!hasOwnTransaction) {
        db.exec("BEGIN");
      }
      db.exec(sql);
      const now = new Date().toISOString();
      db.prepare(
        "INSERT INTO __migrations (version, name, applied_at) VALUES (?, ?, ?)",
      ).run([version, file, now]);
      if (!hasOwnTransaction) {
        db.exec("COMMIT");
      }
      applied.add(version);
    } catch (e) {
      // Ne tenter un ROLLBACK que si on a ouvert une transaction
      if (!hasOwnTransaction) {
        try { db.exec("ROLLBACK"); } catch { /* déjà rollback ou pas de txn ouverte */ }
      }
      throw e;
    }
  }
}

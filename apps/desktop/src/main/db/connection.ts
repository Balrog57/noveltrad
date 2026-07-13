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

  // node-sqlite3-wasm gère le locking SQLite via un DOSSIER `<dbpath>.lock/`
  // (mkdirSync à l'ouverture, rmdirSync au close). Si l'app crashe sans
  // appeler db.close() proprement (OU si un kill -9 / taskkill / panne de
  // courant), ce dossier reste et la DB est PERMANENTMENT verrouillée — toute
  // ouverture ultérieure échoue avec "database is locked" car le mkdirSync
  // retourne EEXIST → SQLITE_BUSY.
  //
  // Recovery : on supprime un éventuel dossier .lock/ stale avant d'ouvrir.
  // C'est sûr car à ce stade aucune connexion n'est active dans CE process, et
  // si une autre instance de l'app tenait réellement la DB, SQLite gérerait le
  // conflit au niveau fichier (le .lock/ serait recréé immédiatement par
  // l'autre process lors de sa prochaine opération). Le seul cas où l'on
  // supprimerait un lock légitime est celui de 2 instances de NovelTrad sur le
  // même projet simultanément — scénario non supporté et déjà problématique.
  const lockDir = `${dbPath}.lock`;
  if (fs.existsSync(lockDir)) {
    try {
      fs.rmSync(lockDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
    } catch {
      // Si la suppression échoue (lock légitime d'un autre process, ou
      // permission), on laisse faire — l'ouverture qui suit échouera avec
      // SQLITE_BUSY et l'utilisateur comprendra qu'un autre process tient la DB.
    }
  }

  const db = new sqlite3.Database(dbPath);
  db.exec("PRAGMA journal_mode = WAL");
  db.exec("PRAGMA foreign_keys = ON");
  // busy_timeout : critique pour éviter "database is locked". Sans cette
  // valeur (SQLite default = 0 ms), toute contention de lock échoue
  // immédiatement avec SQLITE_BUSY. Avec 5000 ms, SQLite retry/attend jusqu'à
  // 5 s avant de lever — élimine la grande majorité des erreurs de lock en
  // présence de lecteurs/écrivains concurrents (IPC handlers vs import/writer).
  db.exec("PRAGMA busy_timeout = 5000");
  // synchronous = NORMAL : safe en WAL (pas de corruption possible, juste un
  // risque minime de perdre la dernière transaction en cas de crash système).
  // Accélère significativement les commits vs le default FULL.
  db.exec("PRAGMA synchronous = NORMAL");
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

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";
import sqlite3 from "node-sqlite3-wasm";
import { runMigrations } from "../../src/main/db/connection";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MIGRATIONS_DIR = path.resolve(
  __dirname,
  "../../src/main/db/migrations",
);

function tableExists(db: sqlite3.Database, table: string): boolean {
  const rows = db
    .prepare(
      "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
    )
    .all([table]) as { name: string }[];
  return rows.length > 0;
}

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

function getMigrations(
  db: sqlite3.Database,
): { version: number; name: string }[] {
  return db
    .prepare("SELECT version, name FROM __migrations ORDER BY version")
    .all() as { version: number; name: string }[];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("runMigrations — v3 consolidated schema", () => {
  let db: sqlite3.Database;

  beforeEach(() => {
    db = new sqlite3.Database();
  });

  afterEach(() => {
    if (db) db.close();
  });

  it("applique les 5 migrations v3 et crée toutes les tables conservées", () => {
    runMigrations(db as never, MIGRATIONS_DIR);

    const rows = getMigrations(db);
    expect(rows).toHaveLength(5);
    expect(rows.map((r) => r.version)).toEqual([1, 2, 3, 4, 5]);
    expect(rows[0].name).toBe("001_initial.sql");
    expect(rows[4].name).toBe("005_prompts.sql");

    // Tables conservées (core)
    expect(tableExists(db, "projects")).toBe(true);
    expect(tableExists(db, "chapters")).toBe(true);
    expect(tableExists(db, "paragraphs")).toBe(true);
    expect(tableExists(db, "settings")).toBe(true);
    // lexicon
    expect(tableExists(db, "lexicon")).toBe(true);
    expect(tableExists(db, "lexicon_aliases")).toBe(true);
    // translation memory
    expect(tableExists(db, "translation_memory")).toBe(true);
    // summaries
    expect(tableExists(db, "chapter_summaries")).toBe(true);
    expect(tableExists(db, "novel_summaries")).toBe(true);
    // prompts (override DB optionnel)
    expect(tableExists(db, "prompts")).toBe(true);
  });

  it("ne crée PAS les tables supprimées en v3", () => {
    runMigrations(db as never, MIGRATIONS_DIR);

    // Tables supprimées (jobs, audit, rag, plugins, calibration, etc.)
    const dropped = [
      "jobs",
      "job_steps",
      "agents",
      "history_snapshots",
      "audit_log",
      "embeddings",
      "exports",
      "statistics",
      "model_calibrations",
      "review_reports",
      "models",
    ];
    for (const t of dropped) {
      expect(tableExists(db, t)).toBe(false);
    }
  });

  it("chapters.metadata et prompts.active existent (consolidés)", () => {
    runMigrations(db as never, MIGRATIONS_DIR);
    expect(columnExists(db, "chapters", "metadata")).toBe(true);
    expect(columnExists(db, "prompts", "active")).toBe(true);
  });

  it("translation_memory.project_id est nullable (entrées globales)", () => {
    runMigrations(db as never, MIGRATIONS_DIR);
    // Insérer une entrée avec project_id NULL doit réussir.
    db.prepare(
      `INSERT INTO translation_memory (id, project_id, source_text, target_text,
        source_language, target_language, created_at)
       VALUES (?, NULL, ?, ?, ?, ?, ?)`,
    ).run(["tm1", "hello", "bonjour", "en", "fr", "2026-01-01"]);
    const row = db
      .prepare("SELECT project_id FROM translation_memory WHERE id = ?")
      .get(["tm1"]) as { project_id: string | null };
    expect(row.project_id).toBeNull();
  });

  it("idempotent : réexécuter ne duplique pas les migrations", () => {
    runMigrations(db as never, MIGRATIONS_DIR);
    runMigrations(db as never, MIGRATIONS_DIR);
    expect(getMigrations(db)).toHaveLength(5);
  });
});

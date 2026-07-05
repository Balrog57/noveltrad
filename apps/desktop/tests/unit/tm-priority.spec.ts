import { describe, it, expect, beforeEach, vi } from "vitest";
import type { TranslationMemoryMatch } from "@shared/types/index.js";
import type { Database } from "node-sqlite3-wasm";

interface MockRow {
  id: string;
  project_id?: string | null;
  source_text: string;
  target_text: string;
  source_language: string;
  target_language: string;
  usage_count: number;
  normalized_hash?: string;
  segment_index?: number;
  is_global?: number;
}

// Mock minimal de la DB pour tester findBestMatch
class MockDb {
  private rows: Map<string, MockRow> = new Map();

  seed(row: MockRow): void {
    this.rows.set(row.id, row);
  }

  prepare(sql: string) {
    return {
      get: (params: unknown[]) => {
        // normalized_hash + project_id + is_global = 0
        if (sql.includes("normalized_hash") && sql.includes("is_global = 0")) {
          const hash = params[0] as string;
          const projectId = params[1] as string;
          for (const row of this.rows.values()) {
            if (row.normalized_hash === hash && row.project_id === projectId && !row.is_global) {
              return { target_text: row.target_text };
            }
          }
          return undefined;
        }
        // normalized_hash + is_global = 1
        if (sql.includes("normalized_hash") && sql.includes("is_global = 1")) {
          const hash = params[0] as string;
          for (const row of this.rows.values()) {
            if (row.normalized_hash === hash && row.is_global === 1) {
              return { target_text: row.target_text };
            }
          }
          return undefined;
        }
        return undefined;
      },
      all: () => [],
      run: (params: unknown[]) => {
        if (sql.includes("INSERT INTO translation_memory")) {
          const row: MockRow = {
            id: params[0] as string,
            project_id: params[1] as string | null,
            source_text: params[2] as string,
            target_text: params[3] as string,
            source_language: (params[4] as string) ?? "",
            target_language: (params[5] as string) ?? "",
            normalized_hash: (params[6] as string) ?? "",
            segment_index: (params[7] as number) ?? 0,
            is_global: (params[8] as number) ?? 0,
            usage_count: 1,
          };
          this.rows.set(row.id, row);
        }
        if (sql.includes("UPDATE translation_memory")) {
          const targetText = params[0] as string;
          const id = params[2] as string;
          const row = this.rows.get(id);
          if (row) {
            row.target_text = targetText;
            row.usage_count += 1;
          }
        }
      },
    };
  }
}

import { TranslationMemoryEngine } from "../../src/main/services/TranslationMemoryEngine";

const NORMALIZE_CACHE: Map<string, string> = new Map();
function normalize(t: string): string {
  if (NORMALIZE_CACHE.has(t)) return NORMALIZE_CACHE.get(t)!;
  const result = t.trim().toLowerCase().replace(/[.,!?;:'"«»()\[\]{}《》「」【】、。，！？；：""''\u2018\u2019\u201c\u201d\u2013\u2014-]/g, "").replace(/\s+/g, " ").trim();
  NORMALIZE_CACHE.set(t, result);
  return result;
}

describe("TranslationMemoryEngine — findBestMatch (5-tier priority)", () => {
  let db: MockDb;
  let engine: TranslationMemoryEngine;
  const PROJECT_ID = "proj-1";

  beforeEach(() => {
    db = new MockDb();
    engine = new TranslationMemoryEngine(db as unknown as Database);
    NORMALIZE_CACHE.clear();
  });

  it("devrait trouver un exact match projet (tier 1) via normalized_hash", () => {
    db.seed({
      id: "1",
      project_id: PROJECT_ID,
      source_text: "Hello world",
      target_text: "Bonjour le monde",
      source_language: "en",
      target_language: "fr",
      usage_count: 1,
      normalized_hash: normalize("Hello world"),
      segment_index: 0,
      is_global: 0,
    });

    // "Hello world!" se normalise en "hello world" comme "Hello world"
    const result = engine.exactMatch("Hello world!", PROJECT_ID);
    expect(result).toBe("Bonjour le monde");
  });

  it("devrait cascader : project exact faih → project fuzzy fail → global exact (tier 3)", () => {
    // Seulement une entrée globale exacte
    db.seed({
      id: "1",
      project_id: null,
      source_text: "Hello world",
      target_text: "Bonjour le monde (global)",
      source_language: "en",
      target_language: "fr",
      usage_count: 1,
      normalized_hash: normalize("Hello world"),
      segment_index: 0,
      is_global: 1,
    });

    // exactMatch project doit retourner null (pas d'entrée projet)
    const projectExact = engine.exactMatch("Hello world!", PROJECT_ID);
    expect(projectExact).toBeNull();

    // exactMatch global doit trouver l'entrée
    const globalExact = engine.exactMatch("Hello world!", null);
    expect(globalExact).toBe("Bonjour le monde (global)");
  });

  it("devrait promouvoir une entrée projet en entrée globale", () => {
    engine.promoteToGlobal("Hello world", "Bonjour le monde (global)", "en", "fr");

    // Vérifier que l'entrée globale existe via exactMatch
    const result = engine.exactMatch("Hello world!", null);
    expect(result).toBe("Bonjour le monde (global)");
  });

  it("devrait normaliser les textes pour augmenter les hits", () => {
    db.seed({
      id: "1",
      project_id: PROJECT_ID,
      source_text: "Hello world",
      target_text: "Bonjour le monde",
      source_language: "en",
      target_language: "fr",
      usage_count: 1,
      normalized_hash: normalize("Hello world"),
      segment_index: 0,
      is_global: 0,
    });

    // "Hello world!" et "Hello world" ont le même hash normalisé
    const hash1 = normalize("Hello world!");
    const hash2 = normalize("Hello world");
    expect(hash1).toBe(hash2);
    expect(hash1).toBe("hello world");

    // exactMatch doit fonctionner même avec ponctuation différente
    const result1 = engine.exactMatch("Hello world!", PROJECT_ID);
    expect(result1).toBe("Bonjour le monde");

    const result2 = engine.exactMatch("Hello world", PROJECT_ID);
    expect(result2).toBe("Bonjour le monde");
  });

  it("devrait retourner null si aucun match dans aucun tiers", () => {
    const result = engine.findBestMatch("Some unknown text", PROJECT_ID);
    expect(result).toBeNull();
  });

  it("promoteToGlobal ne devrait pas planter si la DB n'est pas définie", () => {
    const engineNoDb = new TranslationMemoryEngine();
    expect(() => {
      engineNoDb.promoteToGlobal("Hello", "Bonjour");
    }).not.toThrow();
  });
});

import { describe, it, expect, beforeEach } from "vitest";
import { TranslationMemoryEngine } from "../../src/main/services/TranslationMemoryEngine";
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

class MockDb {
  private rows: Map<string, MockRow> = new Map();

  seed(row: MockRow): void {
    this.rows.set(row.id, row);
  }

  prepare(sql: string) {
    return {
      get: () => undefined,
      all: (params: unknown[]) => {
        // LIKE prefilter: WHERE source_text LIKE ? AND project_id = ? LIMIT ?
        if (sql.includes("LIKE") && sql.includes("project_id = ?")) {
          const likePattern = params[0] as string;
          const projectId = params[1] as string;
          const term = likePattern.replace(/%/g, "").toLowerCase();
          const result: Array<{
            source_text: string;
            target_text: string;
            usage_count: number;
          }> = [];
          for (const row of this.rows.values()) {
            if (
              row.project_id === projectId &&
              row.source_text.toLowerCase().includes(term)
            ) {
              result.push({
                source_text: row.source_text,
                target_text: row.target_text,
                usage_count: row.usage_count,
              });
            }
          }
          return result;
        }
        // Fallback: WHERE project_id = ?
        if (sql.includes("project_id = ?") && !sql.includes("LIKE")) {
          const projectId = params[0] as string;
          const result: Array<{
            source_text: string;
            target_text: string;
            usage_count: number;
          }> = [];
          for (const row of this.rows.values()) {
            if (row.project_id === projectId) {
              result.push({
                source_text: row.source_text,
                target_text: row.target_text,
                usage_count: row.usage_count,
              });
            }
          }
          return result;
        }
        return [];
      },
      run: () => {},
    };
  }
}

const PROJECT_ID = "proj-fuzzy";

describe("TranslationMemoryEngine — fuzzy two-pass (MiniSearch + Levenshtein)", () => {
  let db: MockDb;
  let engine: TranslationMemoryEngine;

  beforeEach(() => {
    db = new MockDb();
    engine = new TranslationMemoryEngine(db as unknown as Database);
  });

  it("devrait trouver des correspondances floues avec le préfiltre MiniSearch", () => {
    db.seed({
      id: "1",
      project_id: PROJECT_ID,
      source_text: "Hello world",
      target_text: "Bonjour le monde",
      source_language: "en",
      target_language: "fr",
      usage_count: 5,
    });
    db.seed({
      id: "2",
      project_id: PROJECT_ID,
      source_text: "Good morning",
      target_text: "Bonjour",
      source_language: "en",
      target_language: "fr",
      usage_count: 3,
    });

    // "Hello world!" est très similaire à "Hello world"
    const matches = engine.fuzzyMatches("Hello world!", PROJECT_ID);
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(matches[0].sourceText).toBe("Hello world");
    expect(matches[0].targetText).toBe("Bonjour le monde");
  });

  it("devrait classer les résultats par score Levenshtein descendant", () => {
    db.seed({
      id: "1",
      project_id: PROJECT_ID,
      source_text: "Hello world",
      target_text: "Bonjour le monde",
      source_language: "en",
      target_language: "fr",
      usage_count: 5,
    });
    db.seed({
      id: "2",
      project_id: PROJECT_ID,
      source_text: "Hello",
      target_text: "Bonjour",
      source_language: "en",
      target_language: "fr",
      usage_count: 3,
    });

    // "Hello world!" est plus proche de "Hello world" (91%) que de "Hello" (67%)
    const matches = engine.fuzzyMatches("Hello world!", PROJECT_ID);
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(matches[0].sourceText).toBe("Hello world");
    expect(matches[0].similarity).toBeGreaterThan(0.85);
  });

  it("devrait retourner un tableau vide si le préfiltre SQL ne trouve rien", () => {
    db.seed({
      id: "1",
      project_id: PROJECT_ID,
      source_text: "Completely different text here",
      target_text: "Texte complètement différent ici",
      source_language: "en",
      target_language: "fr",
      usage_count: 1,
    });

    // "Hello world" n'a rien à voir avec "Completely different text here"
    // et le préfiltre LIKE ne trouvera pas de terme commun
    const matches = engine.fuzzyMatches("Hello world", PROJECT_ID);
    expect(matches).toHaveLength(0);
  });

  it("devrait retourner un tableau vide si la DB n'est pas définie", () => {
    const engineNoDb = new TranslationMemoryEngine();
    const matches = engineNoDb.fuzzyMatches("Hello", PROJECT_ID);
    expect(matches).toEqual([]);
  });

  // ── T12 fix : tokenization Unicode pour CJK (zh/ja/ko) ─────────────────

  it("T12: fuzzy CJK — extrait un terme chinois et trouve des matchs", () => {
    // T12 fix : avant, la regex /\b\w{3,}\b/ ne matchait pas le CJK → le
    // préfiltre LIKE échouait → fuzzy dégradait vers le fallback. Désormais
    // \p{L} matche le CJK et le préfiltre fonctionne.
    db.seed({
      id: "cjk-1",
      project_id: PROJECT_ID,
      source_text: "剑客独行走江湖",
      target_text: "Le swordsmen marchait seul dans le monde",
      source_language: "zh",
      target_language: "fr",
      usage_count: 2,
    });

    const matches = engine.fuzzyMatches("剑客独行走江湖", PROJECT_ID);
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(matches[0].sourceText).toBe("剑客独行走江湖");
  });

  it("T12: fuzzy CJK japonais — terme extrait via \\p{L}", () => {
    db.seed({
      id: "cjk-ja",
      project_id: PROJECT_ID,
      source_text: "剣士は孤独に歩いた",
      target_text: "Le swordsman marchait seul",
      source_language: "ja",
      target_language: "fr",
      usage_count: 1,
    });

    const matches = engine.fuzzyMatches("剣士は孤独に歩いた", PROJECT_ID);
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(matches[0].sourceText).toBe("剣士は孤独に歩いた");
  });
});

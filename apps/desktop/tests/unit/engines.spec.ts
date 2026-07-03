import { describe, it, expect, beforeEach } from "vitest";
import { LexiconEngine } from "../../src/main/services/LexiconEngine";
import { ConsistencyChecker } from "../../src/main/services/ConsistencyChecker";
import { QualityChecker } from "../../src/main/services/QualityChecker";
import { SplitAgent } from "../../src/main/services/agents/SplitAgent";
import { TranslationMemoryEngine } from "../../src/main/services/TranslationMemoryEngine";

describe("LexiconEngine", () => {
  it("applies locked terms", () => {
    const engine = new LexiconEngine();
    const result = engine.apply("The dragon flew.", [
      {
        id: "1",
        projectId: "p1",
        term: "dragon",
        translation: "dragon",
        category: "creature",
        aliases: [],
        locked: true,
        priority: 10,
      },
    ]);
    expect(result.text).toBe("The dragon flew.");
    expect(result.substitutions.length).toBe(1);
  });
});

describe("ConsistencyChecker", () => {
  it("reports paragraph count mismatch", () => {
    const checker = new ConsistencyChecker();
    const report = checker.check(["a", "b"], ["a"], []);
    expect(report.warnings.length).toBeGreaterThan(0);
    expect(report.globalScore).toBeLessThan(100);
  });
});

describe("QualityChecker", () => {
  it("returns a quality report", async () => {
    const checker = new QualityChecker();
    const report = await checker.evaluate(
      "hello world",
      "bonjour le monde",
      [],
    );
    expect(report.globalScore).toBeGreaterThanOrEqual(0);
    expect(report.globalScore).toBeLessThanOrEqual(100);
  });
});

describe("SplitAgent", () => {
  it("splits text into paragraphs", async () => {
    const agent = new SplitAgent({ providerId: "test", model: "test" });
    const output = await agent.execute({
      projectId: "p1",
      text: "First paragraph.\n\nSecond paragraph.",
    });
    expect(output.paragraphs?.length).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// TranslationMemoryEngine — exactMatch, fuzzyMatches, store
// (importTmx/exportTmx are tested in tmx.spec.ts)
// ---------------------------------------------------------------------------

interface TmRow {
  id: string;
  project_id: string;
  source_text: string;
  target_text: string;
  source_language: string;
  target_language: string;
  usage_count: number;
  last_used_at: string | null;
  created_at: string;
}

class MockTmDatabase {
  private rows: Map<string, TmRow> = new Map();

  prepare(sql: string): {
    get: (params: unknown[]) => unknown;
    all: (params: unknown[]) => unknown[];
    run: (params: unknown[]) => void;
  } {
    return {
      get: (params: unknown[]): unknown => {
        // SELECT target_text FROM translation_memory WHERE project_id = ? AND source_text = ?
        if (sql.includes("SELECT target_text") && sql.includes("source_text = ?")) {
          const projectId = params[0] as string;
          const sourceText = params[1] as string;
          for (const row of this.rows.values()) {
            if (row.project_id === projectId && row.source_text === sourceText) {
              return { target_text: row.target_text };
            }
          }
          return undefined;
        }
        // SELECT id FROM translation_memory WHERE project_id = ? AND source_text = ?
        if (sql.includes("SELECT id") && sql.includes("source_text = ?")) {
          const projectId = params[0] as string;
          const sourceText = params[1] as string;
          for (const row of this.rows.values()) {
            if (row.project_id === projectId && row.source_text === sourceText) {
              return { id: row.id };
            }
          }
          return undefined;
        }
        return undefined;
      },
      all: (params: unknown[]): unknown[] => {
        // SELECT source_text, target_text, usage_count FROM translation_memory WHERE project_id = ?
        if (sql.includes("usage_count")) {
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
      run: (params: unknown[]): void => {
        // INSERT INTO translation_memory (...)
        if (sql.includes("INSERT INTO translation_memory")) {
          const row: TmRow = {
            id: params[0] as string,
            project_id: params[1] as string,
            source_text: params[2] as string,
            target_text: params[3] as string,
            source_language: params[4] as string,
            target_language: params[5] as string,
            usage_count: 1,
            last_used_at: null,
            created_at: params[6] as string,
          };
          this.rows.set(row.id, row);
          return;
        }
        // UPDATE translation_memory SET target_text = ?, usage_count = usage_count + 1, last_used_at = ? WHERE id = ?
        if (sql.includes("UPDATE translation_memory")) {
          const targetText = params[0] as string;
          const lastUsedAt = params[1] as string;
          const id = params[2] as string;
          const row = this.rows.get(id);
          if (row) {
            row.target_text = targetText;
            row.usage_count += 1;
            row.last_used_at = lastUsedAt;
          }
          return;
        }
      },
    };
  }

  /** Seed data for testing */
  seed(rows: TmRow[]): void {
    for (const row of rows) {
      this.rows.set(row.id, row);
    }
  }

  get size(): number {
    return this.rows.size;
  }

  getAllRows(): TmRow[] {
    return Array.from(this.rows.values());
  }
}

const PROJECT_ID = "00000000-0000-0000-0000-000000000001";

describe("TranslationMemoryEngine — exactMatch", () => {
  let db: MockTmDatabase;
  let engine: TranslationMemoryEngine;

  beforeEach(() => {
    db = new MockTmDatabase();
    engine = new TranslationMemoryEngine(db as unknown as import("node-sqlite3-wasm").Database);
  });

  it("devrait retourner la traduction exacte si elle existe", () => {
    db.seed([
      {
        id: "1", project_id: PROJECT_ID,
        source_text: "Hello world", target_text: "Bonjour le monde",
        source_language: "en", target_language: "fr",
        usage_count: 1, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
    ]);

    const result = engine.exactMatch("Hello world", PROJECT_ID);
    expect(result).toBe("Bonjour le monde");
  });

  it("devrait retourner null si aucune correspondance exacte", () => {
    db.seed([
      {
        id: "1", project_id: PROJECT_ID,
        source_text: "Hello world", target_text: "Bonjour le monde",
        source_language: "en", target_language: "fr",
        usage_count: 1, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
    ]);

    const result = engine.exactMatch("Goodbye", PROJECT_ID);
    expect(result).toBeNull();
  });

  it("devrait retourner null si la DB n'est pas définie", () => {
    const engineNoDb = new TranslationMemoryEngine();
    const result = engineNoDb.exactMatch("Hello", PROJECT_ID);
    expect(result).toBeNull();
  });
});

describe("TranslationMemoryEngine — fuzzyMatches", () => {
  let db: MockTmDatabase;
  let engine: TranslationMemoryEngine;

  beforeEach(() => {
    db = new MockTmDatabase();
    engine = new TranslationMemoryEngine(db as unknown as import("node-sqlite3-wasm").Database);
  });

  it("devrait retourner des correspondances floues avec similarité > 0.85", () => {
    db.seed([
      {
        id: "1", project_id: PROJECT_ID,
        source_text: "Hello world", target_text: "Bonjour le monde",
        source_language: "en", target_language: "fr",
        usage_count: 5, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
      {
        id: "2", project_id: PROJECT_ID,
        source_text: "Good morning", target_text: "Bonjour",
        source_language: "en", target_language: "fr",
        usage_count: 3, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
    ]);

    // "Hello world!" est très similaire à "Hello world" (91%)
    const matches = engine.fuzzyMatches("Hello world!", PROJECT_ID);
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(matches[0].sourceText).toBe("Hello world");
    expect(matches[0].targetText).toBe("Bonjour le monde");
  });

  it("devrait trier par similarité décroissante", () => {
    db.seed([
      {
        id: "1", project_id: PROJECT_ID,
        source_text: "Hello world", target_text: "Bonjour le monde",
        source_language: "en", target_language: "fr",
        usage_count: 5, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
      {
        id: "2", project_id: PROJECT_ID,
        source_text: "Hello", target_text: "Bonjour",
        source_language: "en", target_language: "fr",
        usage_count: 3, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
    ]);

    // "Hello world!" est plus similaire à "Hello world" (91%) qu'à "Hello" (67%)
    const matches = engine.fuzzyMatches("Hello world!", PROJECT_ID);
    expect(matches.length).toBeGreaterThanOrEqual(1);
    // La meilleure correspondance doit être en premier
    expect(matches[0].sourceText).toBe("Hello world");
    expect(matches[0].similarity).toBeGreaterThan(0.85);
  });

  it("devrait respecter le paramètre limit", () => {
    db.seed([
      {
        id: "1", project_id: PROJECT_ID,
        source_text: "Hello world foo", target_text: "Bonjour le monde foo",
        source_language: "en", target_language: "fr",
        usage_count: 1, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
      {
        id: "2", project_id: PROJECT_ID,
        source_text: "Hello world bar", target_text: "Bonjour le monde bar",
        source_language: "en", target_language: "fr",
        usage_count: 1, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
      {
        id: "3", project_id: PROJECT_ID,
        source_text: "Hello baz", target_text: "Bonjour baz",
        source_language: "en", target_language: "fr",
        usage_count: 1, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
    ]);

    const matches = engine.fuzzyMatches("Hello world", PROJECT_ID, 2);
    expect(matches.length).toBeLessThanOrEqual(2);
  });

  it("devrait filtrer les correspondances en dessous du seuil de 0.85", () => {
    db.seed([
      {
        id: "1", project_id: PROJECT_ID,
        source_text: "Completely different text here", target_text: "Texte complètement différent ici",
        source_language: "en", target_language: "fr",
        usage_count: 1, last_used_at: null, created_at: "2026-01-01T00:00:00.000Z",
      },
    ]);

    // "Hello world" n'a rien à voir avec "Completely different text here"
    const matches = engine.fuzzyMatches("Hello world", PROJECT_ID);
    expect(matches).toHaveLength(0);
  });

  it("devrait retourner un tableau vide si la DB n'est pas définie", () => {
    const engineNoDb = new TranslationMemoryEngine();
    const matches = engineNoDb.fuzzyMatches("Hello", PROJECT_ID);
    expect(matches).toEqual([]);
  });
});

describe("TranslationMemoryEngine — store", () => {
  let db: MockTmDatabase;
  let engine: TranslationMemoryEngine;

  beforeEach(() => {
    db = new MockTmDatabase();
    engine = new TranslationMemoryEngine(db as unknown as import("node-sqlite3-wasm").Database);
  });

  it("devrait insérer une nouvelle entrée", () => {
    engine.store("Hello", "Bonjour", PROJECT_ID, "en", "fr");

    expect(db.size).toBe(1);
    const rows = db.getAllRows();
    expect(rows[0].source_text).toBe("Hello");
    expect(rows[0].target_text).toBe("Bonjour");
    expect(rows[0].source_language).toBe("en");
    expect(rows[0].target_language).toBe("fr");
    expect(rows[0].usage_count).toBe(1);
  });

  it("devrait mettre à jour une entrée existante (usage_count incrémenté)", () => {
    engine.store("Hello", "Bonjour", PROJECT_ID, "en", "fr");
    expect(db.size).toBe(1);

    // Store again — should update + increment usage_count
    engine.store("Hello", "Salut", PROJECT_ID, "en", "fr");
    expect(db.size).toBe(1); // No duplicate

    const rows = db.getAllRows();
    expect(rows[0].target_text).toBe("Salut"); // Updated
    expect(rows[0].usage_count).toBe(2); // Incremented
  });

  it("devrait ne rien faire si la DB n'est pas définie", () => {
    const engineNoDb = new TranslationMemoryEngine();
    expect(() => {
      engineNoDb.store("Hello", "Bonjour", PROJECT_ID, "en", "fr");
    }).not.toThrow();
  });
});

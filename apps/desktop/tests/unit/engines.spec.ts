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

  // ── Dialogues ──

  it("dialogues: mismatch >20% triggers warning", () => {
    const checker = new ConsistencyChecker();
    // source has 0 dialogue markers, target has many
    const source = ["Hello world."];
    const target = ["« Bonjour », dit-il. « Comment vas-tu ? »"];
    const report = checker.check(source, target, []);
    const dialogueWarnings = report.warnings.filter((w) =>
      w.message.includes("dialogue"),
    );
    expect(dialogueWarnings.length).toBeGreaterThan(0);
  });

  it("dialogues: matching counts produce no warning", () => {
    const checker = new ConsistencyChecker();
    const source = ['"Hello," he said, "how are you?"'];
    const target = ['« Bonjour », dit-il, « comment allez-vous ? »'];
    const report = checker.check(source, target, []);
    const dialogueWarnings = report.warnings.filter((w) =>
      w.message.includes("dialogue"),
    );
    expect(dialogueWarnings.length).toBe(0);
  });

  it("dialogues: no dialogue markers does not warn", () => {
    const checker = new ConsistencyChecker();
    const source = ["Hello world this is a simple text."];
    const target = ["Bonjour le monde ceci est un texte simple."];
    const report = checker.check(source, target, []);
    const dialogueWarnings = report.warnings.filter((w) =>
      w.message.includes("dialogue"),
    );
    expect(dialogueWarnings.length).toBe(0);
  });

  // ── Numbers ──

  it("numbers: all present produces no warning", () => {
    const checker = new ConsistencyChecker();
    const source = ["There are 3 apples and 5 oranges."];
    const target = ["Il y a 3 pommes et 5 oranges."];
    const report = checker.check(source, target, []);
    const numberWarnings = report.warnings.filter((w) =>
      w.message.includes("Nombre"),
    );
    expect(numberWarnings.length).toBe(0);
  });

  it("numbers: missing number triggers warning", () => {
    const checker = new ConsistencyChecker();
    const source = ["There are 3 apples and 5 oranges."];
    const target = ["Il y a des pommes et des oranges."];
    const report = checker.check(source, target, []);
    const numberWarnings = report.warnings.filter((w) =>
      w.message.includes("absent de la cible"),
    );
    // Both "3" and "5" are missing → 2 warnings
    expect(numberWarnings.length).toBe(2);
  });

  it("numbers: extra number in target triggers warning", () => {
    const checker = new ConsistencyChecker();
    const source = ["Hello world."];
    const target = ["Bonjour le monde 42."];
    const report = checker.check(source, target, []);
    const numberWarnings = report.warnings.filter((w) =>
      w.message.includes("absent du source"),
    );
    expect(numberWarnings.length).toBe(1);
  });

  // ── Markup ──

  it("markup: mismatch triggers warning", () => {
    const checker = new ConsistencyChecker();
    const source = ["This is **bold** and _italic_."];
    const target = ["Ceci est **bold**."]; // missing _italic_
    const report = checker.check(source, target, []);
    const markupWarnings = report.warnings.filter((w) =>
      w.message.includes("Balises"),
    );
    expect(markupWarnings.length).toBeGreaterThan(0);
  });

  it("markup: matching markup produces no warning", () => {
    const checker = new ConsistencyChecker();
    const source = ["This is **bold** and <em>emphasized</em>."];
    const target = ["Ceci est **gras** et <em>emphase</em>."];
    const report = checker.check(source, target, []);
    const markupWarnings = report.warnings.filter((w) =>
      w.message.includes("Balises"),
    );
    expect(markupWarnings.length).toBe(0);
  });

  it("markup: no markup produces no warning", () => {
    const checker = new ConsistencyChecker();
    const source = ["Hello world."];
    const target = ["Bonjour le monde."];
    const report = checker.check(source, target, []);
    const markupWarnings = report.warnings.filter((w) =>
      w.message.includes("Balises"),
    );
    expect(markupWarnings.length).toBe(0);
  });

  // ── Score formula ──

  it("score formula: weighted average computed correctly", () => {
    const checker = new ConsistencyChecker();
    // Perfect match — all metrics should be 100
    const source = ["Hello world. How are you?"];
    const target = ["Bonjour le monde. Comment allez-vous ?"];
    const report = checker.check(source, target, []);
    expect(report.globalScore).toBe(100);

    // Now force a partial failure: paragraph mismatch
    const report2 = checker.check(["a", "b", "c"], ["a", "b"], []);
    // paragraphs weight=30 → score 0, rest 100
    // weighted = (0*30 + 100*15 + 100*15 + 100*10 + 100*15 + 100*10 + 100*5) / 100
    // = (0 + 1500 + 1500 + 1000 + 1500 + 1000 + 500) / 100 = 7000/100 = 70
    // cap paragraphIssue → ≤50
    expect(report2.globalScore).toBeLessThanOrEqual(50);
  });

  it("score formula: caps applied correctly", () => {
    const checker = new ConsistencyChecker();
    // Missing locked term + missing number = both caps applied
    const source = ["Hello Dr.Martin, call me at 555."];
    const target = ["Bonjour, appelle-moi au 555."]; // Dr.Martin is a locked term missing
    const report = checker.check(source, target, [
      {
        id: "1",
        projectId: "p1",
        term: "Dr.Martin",
        translation: "Dr.Martin",
        category: "name",
        aliases: [],
        locked: true,
        priority: 10,
      },
    ]);
    // lockedNameMissing cap → ≤70
    expect(report.globalScore).toBeLessThanOrEqual(70);
  });

  // ── Tolerances ──

  it("tolerances: zh-fr uses SDD §11.3 bounds", () => {
    const checker = new ConsistencyChecker();
    const tol = checker.getTolerance("zh-fr");
    expect(tol.sentenceRatioMin).toBe(0.95);
    expect(tol.sentenceRatioMax).toBe(1.05);
    expect(tol.lengthRatioMin).toBe(0.5);
    expect(tol.lengthRatioMax).toBe(1.5);
  });

  it("tolerances: unknown pair falls back to default", () => {
    const checker = new ConsistencyChecker();
    const tol = checker.getTolerance("de-es");
    expect(tol.sentenceRatioMin).toBe(0.7);
    expect(tol.sentenceRatioMax).toBe(1.5);
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
  normalized_hash?: string;
  segment_index?: number;
  is_global?: number;
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
        // SELECT target_text FROM translation_memory WHERE normalized_hash = ? AND project_id = ? AND is_global = 0
        if (sql.includes("SELECT target_text") && sql.includes("normalized_hash")) {
          const hash = params[0] as string;
          // Project-level exact
          if (sql.includes("is_global = 0")) {
            const projectId = params[1] as string;
            for (const row of this.rows.values()) {
              if (row.normalized_hash === hash && row.project_id === projectId && !row.is_global) {
                return { target_text: row.target_text };
              }
            }
            return undefined;
          }
          // Global exact (is_global = 1)
          if (sql.includes("is_global = 1")) {
            for (const row of this.rows.values()) {
              if (row.normalized_hash === hash && row.is_global === 1) {
                return { target_text: row.target_text };
              }
            }
            return undefined;
          }
          return undefined;
        }
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
        // SELECT id FROM translation_memory WHERE project_id = ? AND normalized_hash = ? AND segment_index = ?
        if (sql.includes("SELECT id") && sql.includes("normalized_hash")) {
          const projectId = params[0] as string;
          const hash = params[1] as string;
          const segIdx = params[2] as number;
          for (const row of this.rows.values()) {
            if (row.project_id === projectId && row.normalized_hash === hash && row.segment_index === segIdx) {
              return { id: row.id };
            }
          }
          return undefined;
        }
        // SELECT id FROM translation_memory WHERE normalized_hash = ? AND is_global = 1
        if (sql.includes("SELECT id") && sql.includes("is_global")) {
          const hash = params[0] as string;
          for (const row of this.rows.values()) {
            if (row.normalized_hash === hash && row.is_global === 1) {
              return { id: row.id };
            }
          }
          return undefined;
        }
        return undefined;
      },
      all: (params: unknown[]): unknown[] => {
        const result: Array<{
          source_text: string;
          target_text: string;
          usage_count: number;
        }> = [];

        // SELECT source_text, target_text, usage_count FROM translation_memory WHERE project_id = ?
        if (sql.includes("usage_count") && sql.includes("project_id = ?") && !sql.includes("LIKE")) {
          const projectId = params[0] as string;
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

        // SELECT ... WHERE source_text LIKE ? AND project_id = ? LIMIT ?
        if (sql.includes("LIKE") && sql.includes("project_id = ?")) {
          const likePattern = params[0] as string;
          const projectId = params[1] as string;
          const term = likePattern.replace(/%/g, "").toLowerCase();
          for (const row of this.rows.values()) {
            if (row.project_id === projectId && row.source_text.toLowerCase().includes(term)) {
              result.push({
                source_text: row.source_text,
                target_text: row.target_text,
                usage_count: row.usage_count,
              });
            }
          }
          return result;
        }

        // SELECT ... WHERE source_text LIKE ? AND is_global = 1 LIMIT ?
        if (sql.includes("LIKE") && sql.includes("is_global")) {
          const likePattern = params[0] as string;
          const term = likePattern.replace(/%/g, "").toLowerCase();
          for (const row of this.rows.values()) {
            if (row.is_global === 1 && row.source_text.toLowerCase().includes(term)) {
              result.push({
                source_text: row.source_text,
                target_text: row.target_text,
                usage_count: row.usage_count,
              });
            }
          }
          return result;
        }

        // SELECT ... FROM translation_memory WHERE is_global = 1 (fallback)
        if (sql.includes("usage_count") && sql.includes("is_global = 1") && !sql.includes("LIKE")) {
          for (const row of this.rows.values()) {
            if (row.is_global === 1) {
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
        // INSERT INTO translation_memory (...) with all fields
        if (sql.includes("INSERT INTO translation_memory")) {
          const row: TmRow = {
            id: params[0] as string,
            project_id: params[1] as string,
            source_text: params[2] as string,
            target_text: params[3] as string,
            source_language: params[4] as string,
            target_language: params[5] as string,
            normalized_hash: (params[6] as string) ?? "",
            segment_index: (params[7] as number) ?? 0,
            is_global: (params[8] as number) ?? 0,
            usage_count: 1,
            last_used_at: null,
            created_at: params[9] as string,
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
        normalized_hash: "hello world",
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
        normalized_hash: "hello world",
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

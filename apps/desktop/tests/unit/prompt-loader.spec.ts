import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock electron-log before any imports that trigger the logger
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    transports: { file: { level: false }, console: { level: false } },
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import { PromptLoader } from "../../src/main/services/prompts/PromptLoader";
import { TRANSLATE_SYSTEM_PROMPT } from "../../src/main/services/prompts/translate.system";
import { CONSISTENCY_SYSTEM_PROMPT } from "../../src/main/services/prompts/consistency.system";
import { STYLE_SYSTEM_PROMPT } from "../../src/main/services/prompts/style.system";

// ---------------------------------------------------------------------------
// Mock DB : mimique le pattern node-sqlite3-wasm utilisé par AiCache, etc.
// ---------------------------------------------------------------------------

type PromptsRow = {
  id: string;
  content: string;
  version: number;
  active: number;
};

class MockPromptDb {
  private data: PromptsRow[] = [];

  prepare(sql: string): {
    get: (params: unknown[]) => unknown;
    all: (params?: unknown[]) => unknown[];
    run: (params: unknown[]) => void;
  } {
    return {
      get: (params: unknown[]): unknown => {
        if (sql.includes("SELECT content FROM prompts WHERE id = ? AND active = 1")) {
          const id = params[0] as string;
          const active = this.data
            .filter((r) => r.id === id && r.active === 1)
            .sort((a, b) => b.version - a.version);
          return active.length > 0 ? { content: active[0].content } : undefined;
        }
        return undefined;
      },

      all: (params?: unknown[]): unknown[] => {
        if (sql.includes("SELECT id, content, version FROM prompts WHERE active = 1")) {
          return this.data
            .filter((r) => r.active === 1)
            .map((r) => ({ id: r.id, content: r.content, version: r.version }));
        }
        return [];
      },

      run: (params: unknown[]): void => {
        if (sql.includes("UPDATE prompts SET active = 0")) {
          const id = params[0] as string;
          for (const row of this.data) {
            if (row.id === id && row.active === 1) {
              row.active = 0;
            }
          }
        }
      },
    };
  }

  /** Helper pour injecter des données de test */
  seed(rows: PromptsRow[]): void {
    this.data = [...rows];
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PromptLoader", () => {
  let db: MockPromptDb;
  let loader: PromptLoader;

  beforeEach(() => {
    db = new MockPromptDb();
    loader = new PromptLoader(db as unknown as import("node-sqlite3-wasm").Database);
  });

  // --- Test 1 : Prompt trouvé en DB → retourné ---
  it("1. devrait retourner le contenu DB quand le prompt est présent et actif", async () => {
    db.seed([
      { id: "translate", content: "DB override version", version: 1, active: 1 },
    ]);
    const result = await loader.load("translate");
    expect(result).toBe("DB override version");
  });

  // --- Test 2 : Prompt absent DB → fallback constante TS ---
  it("2. devrait utiliser la constante TS quand le prompt est absent de la DB", async () => {
    // Pas de seed → DB vide
    const result = await loader.load("translate");
    expect(result).toBe(TRANSLATE_SYSTEM_PROMPT);
  });

  // --- Test 3 : Version DB invalide (valeur vide) → fallback ---
  it("3. devrait fallback sur la constante TS quand la version DB a un contenu vide", async () => {
    db.seed([
      { id: "consistency", content: "", version: 2, active: 1 },
    ]);
    const result = await loader.load("consistency");
    expect(result).toBe(CONSISTENCY_SYSTEM_PROMPT);
  });

  // --- Test 4 : listCustomPrompts() retourne les overrides actifs ---
  it("4. listCustomPrompts() devrait retourner les prompts DB actifs", () => {
    db.seed([
      { id: "translate", content: "Custom translate", version: 1, active: 1 },
      { id: "consistency", content: "Custom consistency", version: 1, active: 1 },
    ]);
    const custom = loader.listCustomPrompts();
    expect(custom).toHaveLength(2);
    expect(custom.find((p) => p.id === "translate")?.content).toBe("Custom translate");
    expect(custom.find((p) => p.id === "consistency")?.content).toBe("Custom consistency");
  });

  // --- Test 5 : resetToDefault() désactive l'override ---
  it("5. resetToDefault() devrait désactiver la version DB et faire fallback sur la constante TS", async () => {
    db.seed([
      { id: "translate", content: "Override", version: 1, active: 1 },
    ]);

    // Avant reset, l'override est chargé
    const before = await loader.load("translate");
    expect(before).toBe("Override");

    // Reset
    loader.resetToDefault("translate");

    // Après reset, fallback sur la constante TS
    const after = await loader.load("translate");
    expect(after).toBe(TRANSLATE_SYSTEM_PROMPT);
  });

  // --- Test 6 : Version multiple → latest active choisie ---
  it("6. devrait charger la version la plus récente quand plusieurs versions actives existent", async () => {
    db.seed([
      { id: "qa", content: "v1 content", version: 1, active: 1 },
      { id: "qa", content: "v2 content", version: 2, active: 1 },
    ]);
    const result = await loader.load("qa");
    expect(result).toBe("v2 content");
  });

  // --- Test 7 : Prompt désactivé (active=0) → fallback ---
  it("7. devrait fallback sur la constante TS quand le prompt DB est désactivé (active=0)", async () => {
    db.seed([
      { id: "style", content: "Disabled override", version: 1, active: 0 },
    ]);
    const result = await loader.load("style");
    expect(result).toBe(STYLE_SYSTEM_PROMPT);
  });

  // --- Test 8 : Erreur DB → fallback constante TS (graceful degradation) ---
  it("8. devrait fallback sur la constante TS en cas d'erreur DB", async () => {
    // Simule une erreur DB en cassant la méthode prepare
    const brokenDb = {
      prepare: () => {
        throw new Error("DB corruption");
      },
    };
    const brokenLoader = new PromptLoader(
      brokenDb as unknown as import("node-sqlite3-wasm").Database,
    );
    const result = await brokenLoader.load("translate");
    expect(result).toBe(TRANSLATE_SYSTEM_PROMPT);
  });

  // --- Test 8b : PromptId inconnu (ni DB, ni fallback) → erreur ---
  it("8b. devrait lever une erreur si le promptId n'existe ni en DB ni dans le fallback", async () => {
    await expect(loader.load("nonexistent-prompt-id")).rejects.toThrow(
      "Prompt inconnu : nonexistent-prompt-id",
    );
  });
});

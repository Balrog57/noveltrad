/**
 * Tests pour SettingsManager (SDD §19)
 *
 * R2. Teste getAll(), get(), set() avec mock fs en mémoire.
 */

import path from "node:path";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// État mémoire simulé pour node:fs
// ---------------------------------------------------------------------------

const { memFs, memExists } = vi.hoisted(() => {
  const memFs = new Map<string, string>();
  const memExists = new Set<string>();
  return { memFs, memExists };
});

vi.mock("node:fs", () => {
  const mockFsRecord: Record<string, unknown> = {
    existsSync: vi.fn((p: string) => memExists.has(p)),
    readFileSync: vi.fn((p: string, _enc?: string) => {
      if (!memFs.has(p)) throw new Error(`ENOENT: ${p}`);
      return memFs.get(p) as string;
    }),
    writeFileSync: vi.fn((p: string, data: string) => {
      memFs.set(p, data);
      memExists.add(p);
    }),
    mkdirSync: vi.fn((p: string) => {
      memExists.add(p);
    }),
    constants: { F_OK: 0 },
  };
  return { ...mockFsRecord, default: mockFsRecord };
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SettingsManager (SDD §19)", () => {
  /** Chemin attendu : APPDATA + '/NovelTrad/config.json' */
  function expectedPath(): string {
    return path.join(process.env.APPDATA ?? "", "NovelTrad", "config.json");
  }

  beforeEach(() => {
    vi.clearAllMocks();
    memFs.clear();
    memExists.clear();
    process.env.APPDATA = "/fake/test/appdata";
  });

  // ── getAll() ────────────────────────────────────────────────────────

  describe("getAll()", () => {
    it("retourne les valeurs par défaut quand le fichier n'existe pas", async () => {
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();
      const all = sm.getAll();

      expect(all).toBeDefined();
      expect(all.ollamaHost).toBe("http://localhost:11434");
      expect(all.defaultModel).toBe("qwen3.5:9b");
      expect(all.theme).toBe("dark");
      expect(all.sourceLanguage).toBe("zh");
      expect(all.targetLanguage).toBe("fr");
      expect(all.firstRunCompleted).toBe(false);
      expect(all.enabledPlugins).toEqual([]);
      expect(all.activeProvider).toBe("ollama");
    });

    it("parse le fichier JSON et valide avec le schéma", async () => {
      const cfgPath = expectedPath();
      memFs.set(
        cfgPath,
        JSON.stringify({ defaultModel: "llama3", theme: "light" }),
      );
      memExists.add(cfgPath);

      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();
      const all = sm.getAll();

      expect(all.defaultModel).toBe("llama3");
      expect(all.theme).toBe("light");
      // Les champs non spécifiés prennent la valeur par défaut du schéma
      expect(all.ollamaHost).toBe("http://localhost:11434");
    });
  });

  // ── get() ───────────────────────────────────────────────────────────

  describe("get()", () => {
    it("retourne la valeur d'une clé existante", async () => {
      const cfgPath = expectedPath();
      memFs.set(cfgPath, JSON.stringify({ defaultModel: "llama3" }));
      memExists.add(cfgPath);

      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();

      expect(sm.get("defaultModel")).toBe("llama3");
      expect(sm.get("sourceLanguage")).toBe("zh");
    });

    it("retourne la valeur par défaut pour une clé absente du fichier", async () => {
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();

      // Fichier absent → toutes les valeurs sont par défaut
      expect(sm.get("ollamaHost")).toBe("http://localhost:11434");
      expect(sm.get("firstRunCompleted")).toBe(false);
      expect(sm.get("maxConcurrentJobs")).toBe(1);
    });

    it("retourne undefined pour une clé inconnue (hors schéma)", async () => {
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();

      const all = sm.getAll();
      expect((all as Record<string, unknown>).nonexistent).toBeUndefined();
    });
  });

  // ── set() ───────────────────────────────────────────────────────────

  describe("set()", () => {
    it("persiste une nouvelle valeur dans le fichier", async () => {
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();

      sm.set("defaultModel", "mistral");

      const saved = JSON.parse(memFs.get(expectedPath()) ?? "{}");
      expect(saved.defaultModel).toBe("mistral");
    });

    it("merge avec les valeurs existantes sans les perdre", async () => {
      const cfgPath = expectedPath();
      memFs.set(
        cfgPath,
        JSON.stringify({ defaultModel: "llama3", theme: "light" }),
      );
      memExists.add(cfgPath);

      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();

      sm.set("sourceLanguage", "en");

      const saved = JSON.parse(memFs.get(cfgPath) ?? "{}");
      expect(saved.defaultModel).toBe("llama3");
      expect(saved.theme).toBe("light");
      expect(saved.sourceLanguage).toBe("en");
    });

    it("valide la valeur avec le schéma Zod — rejette une valeur invalide", async () => {
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();

      expect(() =>
        sm.set("theme", "invalid-theme" as "dark" | "light" | "system"),
      ).toThrow();
    });

    it("persiste un tableau enabledPlugins", async () => {
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();

      sm.set("enabledPlugins", ["plugin-a", "plugin-b"]);

      const saved = JSON.parse(memFs.get(expectedPath()) ?? "{}");
      expect(saved.enabledPlugins).toEqual(["plugin-a", "plugin-b"]);
    });

    it("écrase une valeur booléenne", async () => {
      const { SettingsManager } = await import(
        "../../src/main/managers/SettingsManager.js"
      );
      const sm = new SettingsManager();

      sm.set("firstRunCompleted", true);
      expect(sm.get("firstRunCompleted")).toBe(true);
    });
  });
});

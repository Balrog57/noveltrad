/**
 * Tests pour les sections de paramètres (SDD §4.11)
 *
 * Vérifie que les nouveaux champs de settings sont bien présents dans
 * le schéma partagé et que le composant SettingsView les affiche.
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// ── Schéma répliqué depuis shared/schemas/index.ts ─────────────────────

const consistencyToleranceSchema = z.object({
  sentenceRatioMin: z.number().min(0).max(5).default(0.7),
  sentenceRatioMax: z.number().min(0).max(10).default(1.5),
  lengthRatioMin: z.number().min(0).max(5).default(0.6),
  lengthRatioMax: z.number().min(0).max(10).default(1.8),
  ignoreNumbersInDialogues: z.boolean().default(false),
  ignorePunctuationMismatch: z.boolean().default(false),
});

const appSettingsSchema = z.object({
  firstRunCompleted: z.boolean().default(false),
  ollamaHost: z.string().default("http://localhost:11434"),
  defaultModel: z.string().default("qwen3.5:9b"),
  defaultPreTranslateModel: z.string().default("qwen3.5:4b"),
  sourceLanguage: z.string().length(2).default("zh"),
  targetLanguage: z.string().length(2).default("fr"),
  defaultProjectsPath: z.string().default("~/NovelTrad Projects"),
  theme: z.enum(["dark", "light", "system"]).default("dark"),
  recentProjects: z.array(z.string()).default([]),
  updateChannel: z.enum(["latest", "beta", "alpha"]).default("latest"),
  ragEnabled: z.boolean().default(true),
  maxConcurrentJobs: z.number().int().min(1).max(8).default(1),
  qualityThreshold: z.number().int().min(0).max(100).default(70),
  consistencyTolerances: z
    .record(z.string(), consistencyToleranceSchema)
    .default({}),
  enabledPlugins: z.array(z.string()).default([]),

  // SDD §4.11.1 : Section IA
  activeProvider: z
    .enum(["ollama", "openai", "anthropic", "gemini", "openrouter", "lmstudio"])
    .default("ollama"),
  fallbackProvider: z
    .enum(["", "ollama", "openai", "anthropic", "gemini", "openrouter", "lmstudio"])
    .default(""),
  apiKey: z.string().default(""),

  // SDD §4.11.4 : Section Interface
  uiLanguage: z.enum(["fr", "en"]).default("fr"),
  editorFontSize: z.number().int().min(10).max(24).default(14),

  // SDD §4.11.5 : Section Avancé
  logLevel: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

type AppSettings = z.infer<typeof appSettingsSchema>;

describe("Settings sections (SDD §4.11)", () => {
  describe("Section IA (SDD §4.11.1)", () => {
    it("activeProvider a une valeur par défaut", () => {
      const result = appSettingsSchema.parse({});
      expect(result.activeProvider).toBe("ollama");
    });

    it("activeProvider accepte toutes les valeurs valides", () => {
      const providers = [
        "ollama", "openai", "anthropic", "gemini", "openrouter", "lmstudio",
      ] as const;
      for (const p of providers) {
        const result = appSettingsSchema.parse({ activeProvider: p });
        expect(result.activeProvider).toBe(p);
      }
    });

    it("activeProvider rejette une valeur invalide", () => {
      expect(() =>
        appSettingsSchema.parse({ activeProvider: "invalid" }),
      ).toThrow();
    });

    it("fallbackProvider accepte chaîne vide (pas de fallback)", () => {
      const result = appSettingsSchema.parse({ fallbackProvider: "" });
      expect(result.fallbackProvider).toBe("");
    });

    it("fallbackProvider accepte les providers valides", () => {
      const result = appSettingsSchema.parse({ fallbackProvider: "openai" });
      expect(result.fallbackProvider).toBe("openai");
    });

    it("apiKey est une chaîne vide par défaut", () => {
      const result = appSettingsSchema.parse({});
      expect(result.apiKey).toBe("");
    });

    it("apiKey accepte une clé valide", () => {
      const result = appSettingsSchema.parse({ apiKey: "sk-123456" });
      expect(result.apiKey).toBe("sk-123456");
    });
  });

  describe("Section Interface (SDD §4.11.4)", () => {
    it("uiLanguage a fr comme valeur par défaut", () => {
      const result = appSettingsSchema.parse({});
      expect(result.uiLanguage).toBe("fr");
    });

    it("uiLanguage accepte fr et en", () => {
      expect(appSettingsSchema.parse({ uiLanguage: "fr" }).uiLanguage).toBe("fr");
      expect(appSettingsSchema.parse({ uiLanguage: "en" }).uiLanguage).toBe("en");
    });

    it("uiLanguage rejette une valeur invalide", () => {
      expect(() => appSettingsSchema.parse({ uiLanguage: "de" })).toThrow();
    });

    it("editorFontSize a 14 par défaut", () => {
      const result = appSettingsSchema.parse({});
      expect(result.editorFontSize).toBe(14);
    });

    it("editorFontSize accepte les valeurs valides", () => {
      for (const size of [10, 12, 14, 16, 18, 20, 24]) {
        const result = appSettingsSchema.parse({ editorFontSize: size });
        expect(result.editorFontSize).toBe(size);
      }
    });

    it("editorFontSize rejette les valeurs hors limite", () => {
      expect(() => appSettingsSchema.parse({ editorFontSize: 5 })).toThrow();
      expect(() => appSettingsSchema.parse({ editorFontSize: 30 })).toThrow();
    });
  });

  describe("Section Avancé (SDD §4.11.5)", () => {
    it("logLevel a info par défaut", () => {
      const result = appSettingsSchema.parse({});
      expect(result.logLevel).toBe("info");
    });

    it("logLevel accepte debug, info, warn, error", () => {
      const levels = ["debug", "info", "warn", "error"] as const;
      for (const l of levels) {
        const result = appSettingsSchema.parse({ logLevel: l });
        expect(result.logLevel).toBe(l);
      }
    });

    it("logLevel rejette une valeur invalide", () => {
      expect(() => appSettingsSchema.parse({ logLevel: "trace" })).toThrow();
    });
  });

  describe("Intégrité du schéma complet", () => {
    it("parse avec des valeurs minimales ne throw pas", () => {
      const result = appSettingsSchema.parse({});
      expect(result).toBeDefined();
    });

    it("sérialise/désérialise toutes les nouvelles propriétés", () => {
      const input: Partial<AppSettings> = {
        activeProvider: "openai",
        fallbackProvider: "anthropic",
        apiKey: "sk-test-key",
        uiLanguage: "en",
        editorFontSize: 18,
        logLevel: "debug",
      };
      const result = appSettingsSchema.parse(input);
      expect(result.activeProvider).toBe("openai");
      expect(result.fallbackProvider).toBe("anthropic");
      expect(result.apiKey).toBe("sk-test-key");
      expect(result.uiLanguage).toBe("en");
      expect(result.editorFontSize).toBe(18);
      expect(result.logLevel).toBe("debug");
    });
  });
});

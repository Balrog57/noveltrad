import path from "node:path";
import os from "node:os";
import fs from "node:fs";
import { z } from "zod";

/** SDD §11.4 : schéma Zod pour une tolérance de cohérence */
const consistencyToleranceSchema = z.object({
  sentenceRatioMin: z.number().min(0).max(5).default(0.7),
  sentenceRatioMax: z.number().min(0).max(10).default(1.5),
  lengthRatioMin: z.number().min(0).max(5).default(0.6),
  lengthRatioMax: z.number().min(0).max(10).default(1.8),
  ignoreNumbersInDialogues: z.boolean().default(false),
  ignorePunctuationMismatch: z.boolean().default(false),
});

export const appSettingsSchema = z.object({
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
  // SDD §7.9 : concurrence des jobs batch (défaut 1 pour Ollama local)
  maxConcurrentJobs: z.number().int().min(1).max(8).default(1),
  // SDD §12.5 : seuil de qualité minimum (le workflow met en pause si le score est inférieur)
  qualityThreshold: z.number().int().min(0).max(100).default(70),
  // SDD §11.4 : tolérances de cohérence configurables par paire de langues
  consistencyTolerances: z
    .record(z.string(), consistencyToleranceSchema)
    .default({}),
});

export type AppSettings = z.infer<typeof appSettingsSchema>;

export class SettingsManager {
  private readonly configPath: string;

  constructor() {
    const appData = process.env.APPDATA || path.join(os.homedir(), ".config");
    const configDir = path.join(appData, "NovelTrad");
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }
    this.configPath = path.join(configDir, "config.json");
  }

  getAll(): AppSettings {
    if (!fs.existsSync(this.configPath)) {
      return appSettingsSchema.parse({});
    }
    const raw = fs.readFileSync(this.configPath, "utf-8");
    return appSettingsSchema.parse(JSON.parse(raw));
  }

  get<K extends keyof AppSettings>(key: K): AppSettings[K] {
    return this.getAll()[key];
  }

  set<K extends keyof AppSettings>(key: K, value: AppSettings[K]): void {
    const current = this.getAll();
    const next = { ...current, [key]: value };
    appSettingsSchema.parse(next);
    fs.writeFileSync(this.configPath, JSON.stringify(next, null, 2), "utf-8");
  }
}

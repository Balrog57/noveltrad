import path from "node:path";
import os from "node:os";
import fs from "node:fs";
import { z } from "zod";

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

import { z } from "zod";

export * from "./paragraph.js";
export * from "./lexicon.js";
export * from "./export.js";
export * from "./history.js";
export * from "./tmx.js";
export * from "./plugin.js";

export const projectSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  author: z.string().max(100).optional(),
  sourceLanguage: z.string().length(2),
  targetLanguage: z.string().length(2),
  path: z.string().min(1),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export const createProjectSchema = z.object({
  name: z.string().min(1).max(100),
  author: z.string().max(100).optional(),
  sourceLanguage: z.string().length(2),
  targetLanguage: z.string().length(2),
  parentPath: z.string().min(1),
});

export const appSettingsSchema = z.object({
  firstRunCompleted: z.boolean().default(false),
  ollamaHost: z.string().url().default("http://localhost:11434"),
  defaultModel: z.string().default("qwen3.5:9b"),
  defaultPreTranslateModel: z.string().default("qwen3.5:4b"),
  sourceLanguage: z.string().length(2).default("zh"),
  targetLanguage: z.string().length(2).default("fr"),
  defaultProjectsPath: z.string().default("~/NovelTrad Projects"),
  theme: z.enum(["dark", "light", "system"]).default("dark"),
});

export const ipcChannelSchema = z.enum([
  "project:create",
  "project:open",
  "project:list-recent",
  "project:delete",
  "ollama:list-models",
  "ollama:pull-model",
  "ollama:is-available",
  "settings:get",
  "settings:set",
  "workflow:start",
  "workflow:pause",
  "workflow:resume",
  "workflow:retry-step",
  "lexicon:list",
  "lexicon:save",
  "chapter:list",
  "chapter:import",
  "export:run",
  "plugin:list",
  "plugin:enable",
  "plugin:disable",
  "plugin:uninstall",
  "plugin:install",
  "plugin:get-config",
  "plugin:set-config",
  "plugin:request-permissions",
  "plugin:confirm-permissions",
]);

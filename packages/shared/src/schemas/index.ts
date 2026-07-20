import { z } from "zod";

export * from "./paragraph.js";
export * from "./lexicon.js";
export * from "./export.js";
export * from "./history.js";
export * from "./tmx.js";
export * from "./plugin.js";
export * from "./agent-io.js";
export * from "./ipc.js";

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

/** SDD §11.4 : schéma Zod pour une tolérance de cohérence */
const consistencyToleranceSchema = z.object({
  sentenceRatioMin: z.number().min(0).max(5).default(0.7),
  sentenceRatioMax: z.number().min(0).max(10).default(1.5),
  lengthRatioMin: z.number().min(0).max(5).default(0.6),
  lengthRatioMax: z.number().min(0).max(10).default(1.8),
  ignoreNumbersInDialogues: z.boolean().default(false),
  ignorePunctuationMismatch: z.boolean().default(false),
});

/** SDD §3.8 : coût estimé par modèle (providers cloud, null = local/gratuit) */
const modelCostSchema = z.object({
  costPerInputToken: z.number().min(0).default(0),
  costPerOutputToken: z.number().min(0).default(0),
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
  // SDD §7.10 : timeout par étape en ms (défaut 120s). Une étape qui dépasse est abandonnée et retryée.
  stepTimeoutMs: z.number().int().positive().default(120000),
  // SDD §11.4 : tolérances de cohérence configurables par paire de langues
  consistencyTolerances: z
    .record(z.string(), consistencyToleranceSchema)
    .default({}),
  // SDD §3.8 : coût par modèle (clé = model id). Vide = pas de suivi de coût (défaut, Ollama local gratuit).
  modelCosts: z.record(z.string(), modelCostSchema).default({}),
  // SDD §15 : plugins activés (liste des IDs)
  enabledPlugins: z.array(z.string()).default([]),

  // SDD §4.11.1 : provider IA actif
  activeProvider: z
    .enum(["ollama", "openai", "anthropic", "gemini", "openrouter", "lmstudio"])
    .default("ollama"),

  // SDD §4.11.1 : provider de fallback
  fallbackProvider: z
    .enum(["", "ollama", "openai", "anthropic", "gemini", "openrouter", "lmstudio"])
    .default(""),

  // SDD §4.11.1 : clé API pour les providers cloud
  apiKey: z.string().default(""),

  // SDD §4.11.4 : langue de l'interface
  uiLanguage: z.enum(["fr", "en"]).default("fr"),

  // SDD §4.11.4 : taille de police dans l'éditeur
  editorFontSize: z.number().int().min(10).max(24).default(14),

  // SDD §4.11.5 : niveau de log
  logLevel: z.enum(["debug", "info", "warn", "error"]).default("info"),

  // SDD §22.2 : utiliser les Worker threads pour les agents CPU-bound
  useWorkerThreads: z.boolean().default(true),

  // v1.4 SDD §7.12 : activer la boucle de révision pro (review/revise)
  reviewLoopEnabled: z.boolean().default(true),

  // v1.4 SDD §7.13 : activer le Summarizer transverse (cohérence cross-chapitre)
  summarizerEnabled: z.boolean().default(true),

  // SDD §17.9 : vérification automatique des mises à jour
  autoUpdateCheck: z.boolean().default(true),

  // Guards anti-boucle : nb max de retries QA automatiques par chapitre avant
  // pause (défaut 3). Évite qu'un chapitre en boucle de révision ne consomme
  // indéfiniment des appels LLM.
  maxQaRetries: z.number().int().min(0).max(20).default(3),

  // Guards anti-boucle : plafond de tokens (in+out) cumulés par job. Au-delà,
  // le workflow est mis en pause pour review humaine. 0 = désactivé.
  maxJobTokens: z.number().int().min(0).default(50000),
});

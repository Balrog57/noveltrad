/**
 * Schémas Zod pour la validation des payloads IPC (SDD §16.3).
 *
 * WS-2 (clean architecture) : ces schémas étaient auparavant définis en local
 * dans chaque fichier handler IPC (`workflow.ts`, `ollama.ts`, `project.ts`,
 * `plugins.ts`, `settings.ts`, `update.ts`) et **répliqués une seconde fois**
 * dans `tests/unit/ipc-validation.spec.ts` (où la copie était même devenue
 * stale — `workflowStageSchema` manquait `review`/`revise`).
 *
 * Promotion vers `@shared/schemas/ipc.ts` = source unique de vérité, importée
 * par les handlers ET les tests. Toute évolution d'un payload se fait ici.
 *
 * Schémas déjà partagés ailleurs (ne pas dupliquer ici) :
 *   - paragraph/lexicon/export/history/tmx/plugin/agent-io → leurs fichiers
 *   - createProjectSchema, projectSchema, appSettingsSchema → schemas/index.ts
 */

import { z } from "zod";

// ── Primitives partagées par plusieurs handlers ─────────────────────────

/** Chemin de projet non vide (utilisé par workflow + project). */
export const projectPathSchema = z.string().min(1, { message: "projectPath requis" });

/** UUID v4 (project/chapter/job). */
export const projectIdSchema = z.string().uuid();
export const chapterIdSchema = z.string().min(1).optional();
export const jobIdSchema = z.string().min(1, { message: "jobId requis" });
export const stepIdSchema = z.string().min(1, { message: "stepId requis" });

/** Au moins un chapterId non vide. */
export const chapterIdsSchema = z
  .array(z.string().min(1), { message: "chapterIds requis" })
  .min(1, { message: "Au moins un chapterId requis" });

// ── Workflow (SDD §7) ───────────────────────────────────────────────────

/** Les 12 stages du pipeline (SDD §7.1). À garder synchronisé avec WorkflowStage. */
export const workflowStageSchema = z.enum([
  "split",
  "pre_translate",
  "translate",
  "consistency",
  "lexicon",
  "grammar",
  "style",
  "polish",
  "review",
  "revise",
  "qa",
  "export",
]);

/**
 * Schéma d'un job IPC pour `workflow:resume-batch`. On accepte les options
 * via `passthrough()` (rétro-compatibilité avec les jobs persistés).
 */
export const jobSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  chapterId: z.string().optional(),
  chapterIds: z.array(z.string()).optional(),
  type: z.enum(["single", "batch"]),
  status: z.enum([
    "pending",
    "running",
    "paused",
    "completed",
    "failed",
    "cancelled",
  ]),
  startedAt: z.string().optional(),
  finishedAt: z.string().optional(),
  errorMessage: z.string().optional(),
  options: z
    .object({
      sourceLanguage: z.string().optional(),
      targetLanguage: z.string().optional(),
      qualityThreshold: z.number().optional(),
      parallelAgents: z.number().optional(),
    })
    .passthrough()
    .optional(),
  metadata: z.record(z.unknown()).optional(),
  createdAt: z.string(),
});

// ── Ollama (SDD §4.6) ───────────────────────────────────────────────────

export const ollamaHostSchema = z.string().min(1).optional();
export const modelNameSchema = z.string().min(1, { message: "model name requis" });

/**
 * Structure retournée par `ollama:is-available` (SDD §16.3).
 * Permet de faire remonter la cause réelle d'un échec à l'UI (ECONNREFUSED,
 * AbortError, HTTP 500…) pour faciliter le diagnostic côté utilisateur.
 */
export const ollamaAvailabilitySchema = z.object({
  available: z.boolean(),
  host: z.string(),
  error: z.string().optional(),
  errorKind: z
    .enum(["network", "timeout", "http", "parse", "unknown"])
    .optional(),
});

// ── Plugins (SDD §15) ───────────────────────────────────────────────────

/** pluginId (même format que le manifest). */
export const pluginIdSchema = z.string().min(1, { message: "pluginId requis" });

/** Payload `plugin:set-config`. */
export const pluginSetConfigSchema = z.object({
  pluginId: pluginIdSchema,
  config: z.unknown(),
});

/** Payload `plugin:confirm-permissions`. */
export const pluginConfirmPermissionsSchema = z.object({
  approvedIds: z.array(pluginIdSchema, {
    message: "approvedIds doit être un tableau d'IDs",
  }),
  nonce: z.string().min(1, { message: "nonce requis" }),
});

// ── Settings (SDD §16) ──────────────────────────────────────────────────

export const settingsKeySchema = z.string().min(1, { message: "settings key requise" });

// ── Update (SDD §17) ────────────────────────────────────────────────────

export const updateChannelSchema = z.enum(["latest", "beta", "alpha"], {
  message: "Canal invalide. Valeurs acceptées : latest, beta, alpha",
});

// ── Project / source (SDD §5) ───────────────────────────────────────────

/** Payload `source:import-files`. */
export const importFilesSchema = z.object({
  projectId: projectIdSchema,
  filePaths: z.array(z.string().min(1)).min(1).max(50),
});

/** Payload `chapter:import`. */
export const chapterImportSchema = z.object({
  projectId: projectIdSchema,
  filePath: z.string().min(1),
});

/** Payload `project:refresh-source`. */
export const refreshSourceSchema = z.object({
  projectId: projectIdSchema,
  chapterId: z.string().uuid(),
  strategy: z.enum(["replace", "merge", "new-version"]).optional().default("replace"),
});

/** Payload `project:detect-duplicate`. */
export const detectDuplicateSchema = z.object({
  projectId: projectIdSchema,
  filePath: z.string().min(1),
});

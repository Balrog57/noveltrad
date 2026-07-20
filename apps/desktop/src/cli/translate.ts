/**
 * Sous-commande `noveltrad translate` — lance le workflow de traduction.
 *
 * Pilote WorkflowEngine directement (sans IPC, sans BrowserWindow). Le
 * progrès est émis sur stderr via le callback onProgress hook (Phase 3.1).
 *
 * Contraintes CLI :
 *   - useWorkerThreads forcés à false (les workers réimportent electron).
 *   - pluginHost non connecté (la CLI ne gère pas les plugins).
 *   - Si Ollama n'est pas accessible → exit code 2 (OLLAMA_DOWN).
 */

import { getSettingsManager } from "../main/managers/SettingsManager.js";
import { ProjectPathResolver } from "../main/managers/ProjectPathResolver.js";
import { WorkflowEngine, type WorkflowProgress } from "../main/managers/WorkflowEngine.js";
import { createProjectDatabase } from "../main/db/connection.js";
import { ChapterRepository } from "../main/db/repositories/ChapterRepository.js";
import { JobRepository } from "../main/db/repositories/JobRepository.js";
import { OllamaManager } from "../main/managers/OllamaManager.js";
import { ok, err, printProgress, type Result } from "./output.js";

export interface TranslateOptions {
  chapterId?: string;
  wait: boolean;
}

export async function runTranslate(
  projectId: string,
  opts: TranslateOptions,
  _jsonMode: boolean,
): Promise<Result<unknown>> {
  const settings = getSettingsManager();

  // ── 1. Preflight : vérifier Ollama ──────────────────────────────────
  const ollamaHost = settings.get("ollamaHost") as string;
  const ollama = new OllamaManager(settings);
  const availability = await ollama.isAvailable();
  if (!availability.available) {
    return err(
      "OLLAMA_DOWN",
      `Ollama inaccessible sur ${ollamaHost}`,
      { host: ollamaHost, error: availability.error, errorKind: availability.errorKind },
    );
  }

  // ── 2. Résoudre le projet + chapitres ───────────────────────────────
  const resolver = new ProjectPathResolver(settings);
  const projectPath = resolver.resolve(projectId);

  // Forcer useWorkerThreads=false en CLI (les workers réimportent electron).
  // On override ponctuellement sans persister — SettingsManager.set persisterait.
  // Solution : sous-classer ou wrapper. Ici on utilise un proxy qui intercepte
  // le get pour useWorkerThreads.
  const cliSettings = wrapSettingsForCli(settings);

  // ── 3. Lister les chapitres à traduire ──────────────────────────────
  const db = createProjectDatabase(projectPath);
  let chapterIds: string[];
  try {
    const chapterRepo = new ChapterRepository(db);
    const allChapters = chapterRepo.listByProject(projectId);
    if (opts.chapterId) {
      if (!allChapters.find((c) => c.id === opts.chapterId)) {
        return err("NOT_FOUND", `Chapitre introuvable : ${opts.chapterId}`);
      }
      chapterIds = [opts.chapterId];
    } else {
      chapterIds = allChapters.map((c) => c.id);
    }
  } finally {
    db.close();
  }

  if (chapterIds.length === 0) {
    return err("INVALID_ARGS", "Aucun chapitre à traduire — importez d'abord un fichier.");
  }

  // ── 4. Démarrer le workflow ─────────────────────────────────────────
  const engine = new WorkflowEngine(cliSettings, undefined, {
    onProgress: (p: WorkflowProgress) => printProgress(p),
  });

  let jobId: string;
  if (opts.chapterId) {
    const job = await engine.start(projectPath, opts.chapterId);
    jobId = job.id;
  } else {
    const job = await engine.startBatch(projectPath, chapterIds);
    jobId = job.id;
  }

  // ── 5. Attendre la fin (sauf --no-wait) ─────────────────────────────
  if (!opts.wait) {
    return ok({ jobId, status: "started", message: "Workflow démarré — utilisez 'status' pour suivre." });
  }

  // Polling du job jusqu'à fin (running/paused → wait, sinon done).
  const finalJob = await waitForJobCompletion(projectPath, projectId, jobId);
  return ok({
    jobId,
    status: finalJob.status,
    type: finalJob.type,
    startedAt: finalJob.startedAt,
    finishedAt: finalJob.finishedAt,
    costUsd: finalJob.costUsd,
    qaRetryCount: finalJob.qaRetryCount,
    errorMessage: finalJob.errorMessage,
  });
}

/**
 * Wrap un SettingsManager pour forcer useWorkerThreads=false en CLI.
 * Les workers réimportent du code couplé à Electron — inutilisables en CLI.
 * Toutes les autres valeurs passent through au SettingsManager réel.
 */
function wrapSettingsForCli(real: ReturnType<typeof getSettingsManager>): ReturnType<typeof getSettingsManager> {
  return new Proxy(real, {
    get(target, prop: string) {
      if (prop === "get") {
        return (key: string) => {
          if (key === "useWorkerThreads") {return false;}
          return target.get(key as never);
        };
      }
      return Reflect.get(target, prop);
    },
  });
}

/** Attend la fin d'un job en pollant la DB. */
async function waitForJobCompletion(
  projectPath: string,
  _projectId: string,
  jobId: string,
): Promise<{
  id: string;
  status: string;
  type: string;
  startedAt?: string;
  finishedAt?: string;
  costUsd?: number;
  qaRetryCount?: number;
  errorMessage?: string;
}> {
  // On garde une DB ouverte pour le polling (fermée à la fin).
  const db = createProjectDatabase(projectPath);
  const jobRepo = new JobRepository(db);
  try {
    const terminalStates = ["completed", "failed", "cancelled"];
    // Timeout de sécurité : 30 min par chapitre, max 6h.
    const maxWaitMs = Math.min(6 * 60 * 60 * 1000, 30 * 60 * 1000);
    const deadline = Date.now() + maxWaitMs;
    while (Date.now() < deadline) {
      const job = jobRepo.getJob(jobId);
      if (!job) {
        throw new Error(`Job disparu : ${jobId}`);
      }
      if (terminalStates.includes(job.status)) {
        return job;
      }
      // paused = intervention humaine requise (QA trop bas). On retourne l'état.
      if (job.status === "paused") {
        return job;
      }
      // Attendre 2s entre chaque poll (le workflow émet des events sur stderr).
      await new Promise((r) => setTimeout(r, 2000));
    }
    throw new Error(`Timeout: job ${jobId} non terminé après ${maxWaitMs / 1000}s`);
  } finally {
    db.close();
  }
}

// Placeholder pour référence (le code tourne via runTranslate exporté).
export const _translateMeta = { requiresOllama: true };

/**
 * Sous-commande `noveltrad translate` — lance le workflow de traduction v3.
 *
 * Pilote SimpleWorkflowRunner directement (sans IPC, sans BrowserWindow). Le
 * progrès est émis sur stderr via le callback onProgress.
 *
 * v3 : le runner retourne une Promise qui se résout à la fin du pipeline —
 * plus de polling de la jobs table (supprimée). Si --no-wait, on rend la main
 * immédiatement après le démarrage (fire-and-forget via un détachement).
 *
 * Contraintes CLI :
 *   - useWorkerThreads forcés à false (les workers réimportent electron).
 *     Non pertinent en v3 (SimpleWorkflowRunner est in-thread de toute façon).
 *   - Si Ollama n'est pas accessible → exit code 2 (OLLAMA_DOWN).
 */

import { getSettingsManager } from "../main/managers/SettingsManager.js";
import { ProjectPathResolver } from "../main/managers/ProjectPathResolver.js";
import {
  SimpleWorkflowRunner,
  type SimpleProgress,
} from "../main/managers/SimpleWorkflowRunner.js";
import { createProjectDatabase } from "../main/db/connection.js";
import { ChapterRepository } from "../main/db/repositories/ChapterRepository.js";
import { OllamaManager } from "../main/managers/OllamaManager.js";
import { ok, err, type Result } from "./output.js";

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

  // ── 4. Démarrer le workflow v3 ──────────────────────────────────────
  const jobId = `cli-${Date.now()}`;
  const runner = new SimpleWorkflowRunner(projectPath, settings, (p: SimpleProgress) => {
    const label = `[${p.batchChapterIndex !== undefined ? `${p.batchChapterIndex + 1}/${p.batchTotalChapters} ` : ""}${p.stageIndex + 1}/${p.totalStages}]`;
    process.stderr.write(`${label} ${p.stage} — ${p.status}\n`);
  });

  try {
    if (opts.chapterId) {
      // --no-wait : on rend la main avant la fin (le process CLI reste vivant
      // car le runner tourne ; dans un shell pipe c'est acceptable pour un MVP).
      const done = runner.runChapter(jobId, chapterIds[0]!);
      if (!opts.wait) {
        return ok({ jobId, status: "started", message: "Workflow démarré." });
      }
      await done;
    } else {
      const done = runner.runBatch(jobId, chapterIds);
      if (!opts.wait) {
        return ok({ jobId, status: "started", message: "Workflow démarré." });
      }
      await done;
    }
    return ok({ jobId, status: "completed" });
  } catch (e) {
    return err("WORKFLOW_FAILED", (e as Error).message);
  } finally {
    runner.dispose();
  }
}

// Placeholder pour référence (le code tourne via runTranslate exporté).
export const _translateMeta = { requiresOllama: true };

import { ipcMain, BrowserWindow } from "electron";
import { z } from "zod";
import crypto from "node:crypto";
import { SimpleWorkflowRunner } from "../../managers/SimpleWorkflowRunner.js";
import type { SimpleProgress } from "../../managers/SimpleWorkflowRunner.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { ChapterRepository } from "../../db/repositories/ChapterRepository.js";
import type { Job } from "@shared/types/index.js";
// WS-2 : schémas IPC promus vers @shared (source unique, plus de copie stale).
import {
  projectPathSchema,
  chapterIdSchema,
  chapterIdsSchema,
} from "@shared/schemas/ipc.js";
import { logger } from "../../utils/logger.js";

// ── Handlers ──────────────────────────────────────────────────────────

const settings = new SettingsManager();

function getMainWindow(): BrowserWindow | null {
  const wins = BrowserWindow.getAllWindows();
  return wins[0] ?? null;
}

/**
 * Registre des runners actifs, keyé par jobId. Permet à `cancel` de retrouver
 * le runner en cours. Les runners sont disposés (DB close) à la fin du run
 * (succès, erreur, ou cancel) puis retirés du registre.
 *
 * v3 : remplace le Map<string, WorkflowRunner> de l'ancien WorkflowEngine.
 * Pas de concurrence (Ollama local) — un seul runner actif à la fois suffit,
 * mais on garde un Map pour rester safe en cas de batch parallèle futur.
 */
const activeRunners = new Map<string, SimpleWorkflowRunner>();

/** Singleton SettingsManager partagé avec les autres handlers IPC. */
export { settings };

function emitProgress(payload: SimpleProgress): void {
  const win = getMainWindow();
  if (win && !win.isDestroyed()) {
    win.webContents.send("workflow:progress", payload);
  }
}

/** Construit un objet Job minimal mais type-valide pour la réponse IPC. */
function makeJob(
  jobId: string,
  projectPath: string,
  projectId: string,
  type: "single" | "batch",
): Job {
  const now = new Date().toISOString();
  return {
    id: jobId,
    projectId,
    type,
    status: "running",
    startedAt: now,
    createdAt: now,
  };
}

/** Lookup du projet + premier chapitre (fallback) pour un projectPath. */
function resolveProject(projectPath: string): {
  projectId: string;
} {
  const db = createProjectDatabase(projectPath);
  try {
    const project = new ProjectRepository(db).getByPath(projectPath);
    if (!project) {
      throw new Error(`Projet non trouvé : ${projectPath}`);
    }
    return { projectId: project.id };
  } finally {
    db.close();
  }
}

/** Nettoie un runner terminé : dispose la DB + retire du registre. */
function cleanupRunner(jobId: string, runner: SimpleWorkflowRunner): void {
  try {
    runner.dispose();
  } catch (err) {
    logger.warn(`[workflow] dispose failed for job ${jobId}`, err);
  }
  activeRunners.delete(jobId);
}

export function registerWorkflowHandlers(): void {
  ipcMain.handle(
    "workflow:start",
    async (_event, projectPath: unknown, chapterId?: unknown) => {
      const parsed = z
        .object({ projectPath: projectPathSchema, chapterId: chapterIdSchema })
        .parse({ projectPath, chapterId });
      const { projectId } = resolveProject(parsed.projectPath);
      const jobId = crypto.randomUUID();
      const job = makeJob(jobId, parsed.projectPath, projectId, "single");

      const runner = new SimpleWorkflowRunner(
        parsed.projectPath,
        settings,
        emitProgress,
      );
      activeRunners.set(jobId, runner);

      // Fire-and-forget : le job est déjà retourné (le renderer suit via events).
      runner
        .runChapter(jobId, parsed.chapterId!)
        .then(() => cleanupRunner(jobId, runner))
        .catch((err) => {
          logger.error(`[workflow:start] job ${jobId} failed`, err);
          cleanupRunner(jobId, runner);
        });

      return job;
    },
  );

  ipcMain.handle(
    "workflow:start-batch",
    async (_event, projectPath: unknown, chapterIds: unknown) => {
      const parsed = z
        .object({ projectPath: projectPathSchema, chapterIds: chapterIdsSchema })
        .parse({ projectPath, chapterIds });
      const { projectId } = resolveProject(parsed.projectPath);
      const jobId = crypto.randomUUID();
      const job = makeJob(jobId, parsed.projectPath, projectId, "batch");
      job.chapterIds = parsed.chapterIds;

      const runner = new SimpleWorkflowRunner(
        parsed.projectPath,
        settings,
        emitProgress,
      );
      activeRunners.set(jobId, runner);

      runner
        .runBatch(jobId, parsed.chapterIds)
        .then(() => cleanupRunner(jobId, runner))
        .catch((err) => {
          logger.error(`[workflow:start-batch] job ${jobId} failed`, err);
          cleanupRunner(jobId, runner);
        });

      return job;
    },
  );

  ipcMain.handle("workflow:cancel", async (_event, jobId: unknown) => {
    const parsed = z.object({ jobId: z.string() }).parse({ jobId });
    const runner = activeRunners.get(parsed.jobId);
    if (runner) {
      runner.cancel();
    }
    return { ok: true };
  });

  // v3 : pas de jobs table persistée. workflow:list retourne les chapitres
  // du projet avec leur statut (utile pour le dashboard Phase 4).
  ipcMain.handle("workflow:list", async (_event, projectPath: unknown) => {
    const parsed = z
      .object({ projectPath: projectPathSchema })
      .parse({ projectPath });
    const db = createProjectDatabase(parsed.projectPath);
    try {
      const project = new ProjectRepository(db).getByPath(parsed.projectPath);
      if (!project) {
        throw new Error(`Projet non trouvé : ${parsed.projectPath}`);
      }
      const chapters = new ChapterRepository(db).listByProject(project.id);
      // Retourne un résumé par chapitre (id, titre, statut) — shape allégée
      // que le renderer dashboard peut consommer directement.
      return chapters.map((c) => ({
        id: c.id,
        title: c.title,
        status: c.status,
      }));
    } finally {
      db.close();
    }
  });
}

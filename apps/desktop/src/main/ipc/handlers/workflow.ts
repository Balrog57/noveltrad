import { ipcMain, BrowserWindow } from "electron";
import { z } from "zod";
import { WorkflowEngine } from "../../managers/WorkflowEngine.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { JobRepository } from "../../db/repositories/JobRepository.js";
import type { WorkflowStage } from "@shared/types/index.js";
// WS-2 : schémas IPC promus vers @shared (source unique, plus de copie stale).
import {
  projectPathSchema,
  chapterIdSchema,
  jobIdSchema,
  stepIdSchema,
  chapterIdsSchema,
  workflowStageSchema,
  jobSchema,
} from "@shared/schemas/ipc.js";

// ── Handlers ──────────────────────────────────────────────────────────

const settings = new SettingsManager();

function getMainWindow(): BrowserWindow | null {
  const wins = BrowserWindow.getAllWindows();
  return wins[0] ?? null;
}

const workflowEngine = new WorkflowEngine(settings, getMainWindow);

export { workflowEngine };

export function registerWorkflowHandlers(): void {
  ipcMain.handle("workflow:start", async (_event, projectPath: unknown, chapterId?: unknown) => {
    const parsed = z
      .object({ projectPath: projectPathSchema, chapterId: chapterIdSchema })
      .parse({ projectPath, chapterId });
    return workflowEngine.start(parsed.projectPath, parsed.chapterId);
  });

  ipcMain.handle("workflow:start-batch", async (_event, projectPath: unknown, chapterIds: unknown) => {
    const parsed = z
      .object({ projectPath: projectPathSchema, chapterIds: chapterIdsSchema })
      .parse({ projectPath, chapterIds });
    return workflowEngine.startBatch(parsed.projectPath, parsed.chapterIds);
  });

  ipcMain.handle("workflow:pause", async (_event, jobId: unknown) => {
    const parsed = z.object({ jobId: jobIdSchema }).parse({ jobId });
    workflowEngine.pause(parsed.jobId);
    return { ok: true };
  });

  ipcMain.handle("workflow:resume", async (_event, jobId: unknown) => {
    const parsed = z.object({ jobId: jobIdSchema }).parse({ jobId });
    workflowEngine.resume(parsed.jobId);
    return { ok: true };
  });

  ipcMain.handle("workflow:cancel", async (_event, jobId: unknown) => {
    const parsed = z.object({ jobId: jobIdSchema }).parse({ jobId });
    workflowEngine.cancel(parsed.jobId);
    return { ok: true };
  });

  ipcMain.handle("workflow:retry-step", async (_event, jobId: unknown, stepId: unknown) => {
    const parsed = z
      .object({ jobId: jobIdSchema, stepId: stepIdSchema })
      .parse({ jobId, stepId });
    await workflowEngine.retryStep(parsed.jobId, parsed.stepId);
    return { ok: true };
  });

  ipcMain.handle("workflow:retry-from", async (_event, jobId: unknown, stage: unknown) => {
    const parsed = z
      .object({ jobId: jobIdSchema, stage: workflowStageSchema })
      .parse({ jobId, stage });
    await workflowEngine.retryFrom(parsed.jobId, parsed.stage as WorkflowStage);
    return { ok: true };
  });

  ipcMain.handle("workflow:list", async (_event, projectPath: unknown) => {
    const parsed = z.object({ projectPath: projectPathSchema }).parse({ projectPath });
    const db = createProjectDatabase(parsed.projectPath);
    try {
      const project = new ProjectRepository(db).getByPath(parsed.projectPath);
      if (!project) {throw new Error(`Projet non trouve : ${parsed.projectPath}`);}
      return new JobRepository(db).listByProject(project.id);
    } finally {
      db.close();
    }
  });

  // SDD §7.11 : liste les jobs en cours (running/paused) pour la reprise au démarrage
  ipcMain.handle("workflow:list-active", async (_event, projectPath: unknown) => {
    const parsed = z.object({ projectPath: projectPathSchema }).parse({ projectPath });
    const db = createProjectDatabase(parsed.projectPath);
    try {
      return new JobRepository(db).listActive();
    } finally {
      db.close();
    }
  });

  // SDD §7.11 : reprend un job batch interrompu au dernier chapitre non terminé
  ipcMain.handle("workflow:resume-batch", async (_event, projectPath: unknown, job: unknown) => {
    const parsed = z
      .object({ projectPath: projectPathSchema, job: jobSchema })
      .parse({ projectPath, job });
    await workflowEngine.resumeBatch(parsed.projectPath, parsed.job);
    return { ok: true };
  });
}

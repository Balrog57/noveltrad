import { ipcMain, BrowserWindow } from "electron";
import { WorkflowEngine } from "../../managers/WorkflowEngine.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { JobRepository } from "../../db/repositories/JobRepository.js";
import type { Job, WorkflowStage } from "@shared/types/index.js";

const settings = new SettingsManager();

function getMainWindow(): BrowserWindow | null {
  const wins = BrowserWindow.getAllWindows();
  return wins[0] ?? null;
}

const workflowEngine = new WorkflowEngine(settings, getMainWindow);

export function registerWorkflowHandlers(): void {
  ipcMain.handle(
    "workflow:start",
    async (_event, projectPath: string, chapterId?: string) => {
      return workflowEngine.start(projectPath, chapterId);
    },
  );

  ipcMain.handle(
    "workflow:start-batch",
    async (_event, projectPath: string, chapterIds: string[]) => {
      return workflowEngine.startBatch(projectPath, chapterIds);
    },
  );

  ipcMain.handle("workflow:pause", async (_event, jobId: string) => {
    workflowEngine.pause(jobId);
    return { ok: true };
  });

  ipcMain.handle("workflow:resume", async (_event, jobId: string) => {
    workflowEngine.resume(jobId);
    return { ok: true };
  });

  ipcMain.handle("workflow:cancel", async (_event, jobId: string) => {
    workflowEngine.cancel(jobId);
    return { ok: true };
  });

  ipcMain.handle(
    "workflow:retry-step",
    async (_event, jobId: string, stepId: string) => {
      await workflowEngine.retryStep(jobId, stepId);
      return { ok: true };
    },
  );

  ipcMain.handle(
    "workflow:retry-from",
    async (_event, jobId: string, stage: WorkflowStage) => {
      await workflowEngine.retryFrom(jobId, stage);
      return { ok: true };
    },
  );

  ipcMain.handle("workflow:list", async (_event, projectPath: string) => {
    const db = createProjectDatabase(projectPath);
    const project = new ProjectRepository(db).getByPath(projectPath);
    if (!project) throw new Error(`Projet non trouve : ${projectPath}`);
    const jobs = new JobRepository(db).listByProject(project.id);
    db.close();
    return jobs;
  });

  // SDD §7.11 : liste les jobs en cours (running/paused) pour la reprise au démarrage
  ipcMain.handle(
    "workflow:list-active",
    async (_event, projectPath: string) => {
      const db = createProjectDatabase(projectPath);
      const jobs = new JobRepository(db).listActive();
      db.close();
      return jobs;
    },
  );

  // SDD §7.11 : reprend un job batch interrompu au dernier chapitre non terminé
  ipcMain.handle(
    "workflow:resume-batch",
    async (_event, projectPath: string, job: Job) => {
      await workflowEngine.resumeBatch(projectPath, job);
      return { ok: true };
    },
  );
}

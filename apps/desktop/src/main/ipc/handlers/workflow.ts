import { ipcMain, BrowserWindow } from "electron";
import { z } from "zod";
import { WorkflowEngine } from "../../managers/WorkflowEngine.js";
import { SettingsManager } from "../../managers/SettingsManager.js";
import { createProjectDatabase } from "../../db/connection.js";
import { ProjectRepository } from "../../db/repositories/ProjectRepository.js";
import { JobRepository } from "../../db/repositories/JobRepository.js";
import type { Job, WorkflowStage } from "@shared/types/index.js";

// ── Schémas de validation Zod (SDD §16.3) ──────────────────────────────

const projectPathSchema = z.string().min(1, { message: "projectPath requis" });
const chapterIdSchema = z.string().min(1).optional();
const jobIdSchema = z.string().min(1, { message: "jobId requis" });
const stepIdSchema = z.string().min(1, { message: "stepId requis" });
const chapterIdsSchema = z
  .array(z.string().min(1), { message: "chapterIds requis" })
  .min(1, { message: "Au moins un chapterId requis" });

const workflowStageSchema = z.enum([
  "split",
  "pre_translate",
  "translate",
  "consistency",
  "lexicon",
  "grammar",
  "style",
  "polish",
  "qa",
  "export",
]);

const jobSchema: z.ZodType<Job> = z.object({
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

// ── Handlers ──────────────────────────────────────────────────────────

const settings = new SettingsManager();

function getMainWindow(): BrowserWindow | null {
  const wins = BrowserWindow.getAllWindows();
  return wins[0] ?? null;
}

const workflowEngine = new WorkflowEngine(settings, getMainWindow);

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
    const project = new ProjectRepository(db).getByPath(parsed.projectPath);
    if (!project) {throw new Error(`Projet non trouve : ${parsed.projectPath}`);}
    const jobs = new JobRepository(db).listByProject(project.id);
    db.close();
    return jobs;
  });

  // SDD §7.11 : liste les jobs en cours (running/paused) pour la reprise au démarrage
  ipcMain.handle("workflow:list-active", async (_event, projectPath: unknown) => {
    const parsed = z.object({ projectPath: projectPathSchema }).parse({ projectPath });
    const db = createProjectDatabase(parsed.projectPath);
    const jobs = new JobRepository(db).listActive();
    db.close();
    return jobs;
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

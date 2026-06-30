import { EventEmitter } from "node:events";
import path from "node:path";
import type { BrowserWindow } from "electron";
import type {
  AgentInput,
  AgentOutput,
  Chapter,
  Job,
  Paragraph,
  Project,
  Step,
  WorkflowStage,
} from "@shared/types/index.js";
import type { SettingsManager } from "./SettingsManager.js";
import {
  createProjectDatabase,
  runMigrations,
  type ProjectDatabase,
} from "../db/connection.js";
import { ProjectRepository } from "../db/repositories/ProjectRepository.js";
import { ChapterRepository } from "../db/repositories/ChapterRepository.js";
import { ParagraphRepository } from "../db/repositories/ParagraphRepository.js";
import { LexiconRepository } from "../db/repositories/LexiconRepository.js";
import { JobRepository } from "../db/repositories/JobRepository.js";
import { AgentFactory } from "../services/agents/AgentFactory.js";
import { AiRouter } from "../services/AiRouter.js";
import { LexiconEngine } from "../services/LexiconEngine.js";
import { TranslationMemoryEngine } from "../services/TranslationMemoryEngine.js";
import { ConsistencyChecker } from "../services/ConsistencyChecker.js";
import { QualityChecker } from "../services/QualityChecker.js";
import { ExportEngine } from "../services/ExportEngine.js";
import { HistoryRepository } from "../db/repositories/HistoryRepository.js";
import { OllamaProvider } from "../services/providers/OllamaProvider.js";
import { logger } from "../utils/logger.js";

const STAGES: WorkflowStage[] = [
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
];

export interface WorkflowProgress {
  jobId: string;
  projectId: string;
  chapterId?: string;
  step: Step;
  totalSteps: number;
}

class WorkflowRunner extends EventEmitter {
  private db: ProjectDatabase;
  private project: Project;
  private chapter?: Chapter;
  private paragraphs: Paragraph[] = [];
  private job!: Job;
  private steps: Step[] = [];
  private paused = false;
  private cancelled = false;
  private factory: AgentFactory;
  private jobRepo: JobRepository;
  private paragraphRepo: ParagraphRepository;
  private chapterRepo: ChapterRepository;
  private lexiconRepo: LexiconRepository;
  private sourceLanguage: string;
  private targetLanguage: string;

  constructor(
    projectPath: string,
    private settings: SettingsManager,
    private emitProgress: (payload: WorkflowProgress) => void,
  ) {
    super();
    this.db = createProjectDatabase(projectPath);
    runMigrations(this.db, path.join(__dirname, "../../db/migrations"));

    const projectRepo = new ProjectRepository(this.db);
    const found = projectRepo.getByPath(projectPath);
    if (!found) throw new Error(`Projet non trouve : ${projectPath}`);
    this.project = found;

    this.sourceLanguage = this.project.sourceLanguage;
    this.targetLanguage = this.project.targetLanguage;

    this.jobRepo = new JobRepository(this.db);
    this.paragraphRepo = new ParagraphRepository(this.db);
    this.chapterRepo = new ChapterRepository(this.db);
    this.lexiconRepo = new LexiconRepository(this.db);

    const aiRouter = new AiRouter();
    const defaultModel = this.settings.get("defaultModel");
    const ollamaHost = this.settings.get("ollamaHost");
    aiRouter.register(
      new OllamaProvider(
        "ollama-default",
        "Ollama local",
        defaultModel,
        ollamaHost,
      ),
    );

    const lexiconEngine = new LexiconEngine();
    const tmEngine = new TranslationMemoryEngine();
    tmEngine.setDatabase(this.db);

    this.factory = new AgentFactory({
      aiRouter,
      lexiconEngine,
      tmEngine,
      consistencyChecker: new ConsistencyChecker(),
      qualityChecker: new QualityChecker(),
      exportEngine: new ExportEngine(),
    });
  }

  async start(chapterId?: string): Promise<Job> {
    if (chapterId) {
      this.chapter = this.chapterRepo.getById(chapterId);
      if (!this.chapter) throw new Error(`Chapitre non trouve : ${chapterId}`);
      this.paragraphs = this.paragraphRepo.listByChapter(chapterId);
    }

    this.job = {
      id: crypto.randomUUID(),
      projectId: this.project.id,
      chapterId,
      type: "single",
      status: "running",
      startedAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
    };
    this.jobRepo.createJob(this.job);

    this.steps = STAGES.map((stage, index) => ({
      id: crypto.randomUUID(),
      jobId: this.job.id,
      agentId: stage,
      name: this.agentName(stage),
      stage,
      orderIndex: index,
      status: "pending",
      createdAt: new Date().toISOString(),
    }));
    for (const step of this.steps) {
      this.jobRepo.createStep(step);
    }

    this.runSequential().catch((err) => {
      logger.error("Workflow error", err);
      this.job.status = "failed";
      this.job.errorMessage = err instanceof Error ? err.message : String(err);
      this.job.finishedAt = new Date().toISOString();
      this.jobRepo.updateJob(this.job);
    });

    return this.job;
  }

  pause(): void {
    this.paused = true;
  }

  resume(): void {
    this.paused = false;
    this.emit("resume");
  }

  cancel(): void {
    this.cancelled = true;
  }

  async retryStep(stepId: string): Promise<void> {
    const step = this.steps.find((s) => s.id === stepId);
    if (!step) throw new Error(`Etape inconnue : ${stepId}`);
    await this.runStep(step);
  }

  async retryFrom(stage: WorkflowStage): Promise<void> {
    const startIndex = STAGES.indexOf(stage);
    if (startIndex === -1) throw new Error(`Stage inconnu : ${stage}`);
    for (let i = startIndex; i < this.steps.length; i++) {
      const step = this.steps[i];
      step.status = "pending";
      step.errorMessage = undefined;
      step.startedAt = undefined;
      step.finishedAt = undefined;
      this.jobRepo.updateStep(step);
    }
    this.job.status = "running";
    this.job.errorMessage = undefined;
    this.jobRepo.updateJob(this.job);
    await this.runFromIndex(startIndex);
  }

  private agentName(stage: WorkflowStage): string {
    const names: Record<WorkflowStage, string> = {
      split: "Decoupage",
      pre_translate: "Pre-traduction",
      translate: "Traduction IA",
      consistency: "Coherence",
      lexicon: "Lexique",
      grammar: "Grammaire",
      style: "Style",
      polish: "Polish",
      qa: "QA",
      export: "Export",
    };
    return names[stage];
  }

  private async runSequential(): Promise<void> {
    await this.runFromIndex(0);
  }

  private async runFromIndex(startIndex: number): Promise<void> {
    for (let i = startIndex; i < this.steps.length; i++) {
      if (this.cancelled) {
        this.job.status = "cancelled";
        this.jobRepo.updateJob(this.job);
        return;
      }

      while (this.paused) {
        await this.waitForResume();
      }

      const step = this.steps[i];
      await this.runStep(step);

      if (step.status === "failed") {
        this.job.status = "failed";
        this.jobRepo.updateJob(this.job);
        return;
      }
    }

    this.job.status = "completed";
    this.job.finishedAt = new Date().toISOString();
    this.jobRepo.updateJob(this.job);
    if (this.chapter) {
      this.chapterRepo.updateStatus(this.chapter.id, "completed");
    }
    // Sauvegarder un snapshot d'historique à la fin d'un workflow réussi
    if (this.chapter && this.paragraphs.length > 0) {
      const historyRepo = new HistoryRepository(this.db);
      const lastStep = this.steps[this.steps.length - 1];
      historyRepo.create({
        id: crypto.randomUUID(),
        projectId: this.project.id,
        chapterId: this.chapter.id,
        jobId: this.job.id,
        stepId: lastStep?.id,
        stage: lastStep?.stage ?? "completed",
        paragraphs: this.paragraphs,
        triggeredBy: "workflow",
      });
    }
    this.db.close();
  }

  private waitForResume(): Promise<void> {
    return new Promise((resolve) => {
      const onResume = (): void => {
        this.off("resume", onResume);
        resolve();
      };
      this.once("resume", onResume);
    });
  }

  private async runStep(step: Step): Promise<AgentOutput | undefined> {
    step.status = "running";
    step.startedAt = new Date().toISOString();
    this.jobRepo.updateStep(step);
    this.emitProgress({
      jobId: this.job.id,
      projectId: this.project.id,
      chapterId: this.chapter?.id,
      step,
      totalSteps: this.steps.length,
    });

    const startTime = Date.now();
    let output: AgentOutput | undefined;

    try {
      const agent = this.factory.create(step.stage, {
        providerId: "ollama-default",
        model: this.settings.get("defaultModel"),
        temperature: 0.7,
      });

      const input = this.buildAgentInput(step.stage);
      step.inputSnapshot = JSON.stringify(input);
      this.jobRepo.updateStep(step);

      output = await agent.execute(input);

      await this.applyAgentOutput(step.stage, output);

      step.status = "completed";
      step.score = output.score;
      step.outputSnapshot = JSON.stringify(output);
    } catch (err) {
      logger.error(`Step ${step.stage} failed`, err);
      step.status = "failed";
      step.errorMessage = err instanceof Error ? err.message : String(err);
      this.jobRepo.updateStep(step);
      this.emitProgress({
        jobId: this.job.id,
        projectId: this.project.id,
        chapterId: this.chapter?.id,
        step,
        totalSteps: this.steps.length,
      });
      return undefined;
    }

    step.finishedAt = new Date().toISOString();
    step.durationMs = Date.now() - startTime;
    this.jobRepo.updateStep(step);
    this.emitProgress({
      jobId: this.job.id,
      projectId: this.project.id,
      chapterId: this.chapter?.id,
      step,
      totalSteps: this.steps.length,
    });

    return output;
  }

  private buildAgentInput(stage: WorkflowStage): AgentInput {
    const lexicon = this.lexiconRepo.listByProject(this.project.id);
    const base: AgentInput = {
      projectId: this.project.id,
      chapterId: this.chapter?.id,
      paragraphs: this.paragraphs,
      lexicon,
      options: {
        sourceLanguage: this.sourceLanguage,
        targetLanguage: this.targetLanguage,
        title: this.chapter?.title ?? "Export",
      },
    };

    switch (stage) {
      case "split":
        return {
          ...base,
          text: this.paragraphs.map((p) => p.sourceText).join("\n\n"),
          paragraphs: undefined,
        };
      case "lexicon":
      case "grammar":
      case "style":
      case "polish":
        return {
          ...base,
          text: this.paragraphs.map((p) => p.translatedText ?? "").join("\n\n"),
          paragraphs: undefined,
        };
      case "export":
        return {
          ...base,
          options: {
            ...base.options,
            format: "markdown",
            outputPath: path.join(this.project.path, "exports"),
          },
        };
      default:
        return base;
    }
  }

  private async applyAgentOutput(
    stage: WorkflowStage,
    output: AgentOutput,
  ): Promise<void> {
    if (output.paragraphs) {
      this.paragraphs = output.paragraphs.map((p, index) => ({
        ...p,
        chapterId: this.chapter?.id ?? p.chapterId,
        indexInChapter: p.indexInChapter ?? index + 1,
      }));
      if (this.chapter) {
        this.paragraphRepo.updateMany(this.paragraphs);
      }
    }

    if (
      output.text &&
      ["lexicon", "grammar", "style", "polish"].includes(stage)
    ) {
      const parts = output.text.split(/\n\n+/);
      this.paragraphs = this.paragraphs.map((p, i) => ({
        ...p,
        translatedText: parts[i] ?? p.translatedText ?? "",
      }));
      if (this.chapter) {
        this.paragraphRepo.updateMany(this.paragraphs);
      }
    }
  }
}

export class WorkflowEngine {
  private runners = new Map<string, WorkflowRunner>();

  constructor(
    private settings: SettingsManager,
    private getMainWindow?: () => BrowserWindow | null,
  ) {}

  private emitProgress(payload: WorkflowProgress): void {
    const win = this.getMainWindow?.();
    if (win && !win.isDestroyed()) {
      win.webContents.send("workflow:progress", payload);
    }
  }

  async start(projectPath: string, chapterId?: string): Promise<Job> {
    const runner = new WorkflowRunner(projectPath, this.settings, (p) =>
      this.emitProgress(p),
    );
    const job = await runner.start(chapterId);
    this.runners.set(job.id, runner);
    return job;
  }

  pause(jobId: string): void {
    this.runners.get(jobId)?.pause();
  }

  resume(jobId: string): void {
    this.runners.get(jobId)?.resume();
  }

  cancel(jobId: string): void {
    this.runners.get(jobId)?.cancel();
  }

  async retryStep(jobId: string, stepId: string): Promise<void> {
    await this.runners.get(jobId)?.retryStep(stepId);
  }

  async retryFrom(jobId: string, stage: WorkflowStage): Promise<void> {
    await this.runners.get(jobId)?.retryFrom(stage);
  }
}

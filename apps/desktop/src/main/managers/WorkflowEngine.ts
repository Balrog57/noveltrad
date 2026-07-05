import { EventEmitter } from "node:events";
import path from "node:path";
import PQueue from "p-queue";
import type { BrowserWindow } from "electron";
import type {
  AgentInput,
  AgentOutput,
  Chapter,
  Job,
  Paragraph,
  Project,
  RagMatch,
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
import { CalibrationService } from "../services/CalibrationService.js";
import { HistoryRepository } from "../db/repositories/HistoryRepository.js";
import { RagEngine } from "../services/RagEngine.js";
import { AiCache } from "../services/AiCache.js";
import { OllamaProvider } from "../services/providers/OllamaProvider.js";
import {
  PerformanceProfiler,
  type PerformanceMetrics,
} from "../services/PerformanceProfiler.js";
import { logger } from "../utils/logger.js";
import { runAgentInWorker } from "../workers/agent-worker.js";

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
  /** Index du chapitre en cours dans un batch (0-based) */
  batchChapterIndex?: number;
  /** Nombre total de chapitres dans le batch */
  batchTotalChapters?: number;
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
  private ragEngine?: RagEngine;
  private sourceLanguage: string;
  private targetLanguage: string;
  private profiler: PerformanceProfiler;

  constructor(
    projectPath: string,
    private settings: SettingsManager,
    private emitProgress: (payload: WorkflowProgress) => void,
    private emitQualityFailed?: (payload: { jobId: string; score: number; threshold: number }) => void,
    profiler?: PerformanceProfiler,
  ) {
    super();
    this.profiler = profiler ?? new PerformanceProfiler();
    this.db = createProjectDatabase(projectPath);
    runMigrations(this.db, path.join(__dirname, "../../db/migrations"));

    const projectRepo = new ProjectRepository(this.db);
    const found = projectRepo.getByPath(projectPath);
    if (!found) {throw new Error(`Projet non trouve : ${projectPath}`);}
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

    // SDD §22.1 : activer le cache des réponses IA
    const aiCache = new AiCache(this.db);
    aiRouter.setCache(aiCache);

    const lexiconEngine = new LexiconEngine();
    const tmEngine = new TranslationMemoryEngine();
    tmEngine.setDatabase(this.db);

    // Initialiser le moteur RAG si activé dans les paramètres
    const ragEnabled = this.settings.get("ragEnabled");
    if (ragEnabled) {
      this.ragEngine = new RagEngine(this.db, ollamaHost);
    }

    const exportEngine = new ExportEngine();
    exportEngine.setDatabase(this.db);

    // SDD §12.5 : service de calibration des scores de qualité
    const calibrationService = new CalibrationService(this.db);

    this.factory = new AgentFactory({
      aiRouter,
      lexiconEngine,
      tmEngine,
      consistencyChecker: new ConsistencyChecker(),
      qualityChecker: new QualityChecker(),
      exportEngine,
      calibrationService,
    });
  }

  async start(chapterId?: string): Promise<Job> {
    return this.runSingle(chapterId);
  }

  async startBatch(chapterIds: string[]): Promise<Job> {
    if (chapterIds.length === 0) {throw new Error("Aucun chapitre selectionne");}

    this.job = {
      id: crypto.randomUUID(),
      projectId: this.project.id,
      chapterIds,
      type: "batch",
      status: "running",
      startedAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      metadata: { batchChapterIndex: 0 },
    };
    this.jobRepo.createJob(this.job);

    this.runBatch(chapterIds, 0).catch((err) => {
      logger.error("Batch workflow error", err);
      this.job.status = "failed";
      this.job.errorMessage = err instanceof Error ? err.message : String(err);
      this.job.finishedAt = new Date().toISOString();
      this.jobRepo.updateJob(this.job);
    });

    return this.job;
  }

  /**
   * SDD §7.11 : Reprend un job batch interrompu (crash / fermeture app).
   * Repart du dernier chapitre non terminé (batchChapterIndex stocké dans metadata).
   */
  async resumeBatch(job: Job): Promise<void> {
    if (
      job.type !== "batch" ||
      !job.chapterIds ||
      job.chapterIds.length === 0
    ) {
      throw new Error("Job non éligible à la reprise batch.");
    }
    const startIndex = Number(job.metadata?.batchChapterIndex ?? 0);
    this.job = { ...job, status: "running" };
    this.jobRepo.updateJob(this.job);

    this.runBatch(job.chapterIds, startIndex).catch((err) => {
      logger.error("Batch resume error", err);
      this.job.status = "failed";
      this.job.errorMessage = err instanceof Error ? err.message : String(err);
      this.job.finishedAt = new Date().toISOString();
      this.jobRepo.updateJob(this.job);
    });
  }

  private async runSingle(chapterId?: string): Promise<Job> {
    if (chapterId) {
      this.chapter = this.chapterRepo.getById(chapterId);
      if (!this.chapter) {throw new Error(`Chapitre non trouve : ${chapterId}`);}
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

  private async runBatch(chapterIds: string[], startIndex = 0): Promise<void> {
    for (
      let batchIndex = startIndex;
      batchIndex < chapterIds.length;
      batchIndex++
    ) {
      if (this.cancelled) {
        this.job.status = "cancelled";
        this.jobRepo.updateJob(this.job);
        return;
      }

      while (this.paused) {
        await this.waitForResume();
      }

      // SDD §7.11 : persister l'index du chapitre en cours pour la reprise après interruption
      this.job.metadata = {
        ...this.job.metadata,
        batchChapterIndex: batchIndex,
      };
      this.jobRepo.updateJob(this.job);

      this.chapter = this.chapterRepo.getById(chapterIds[batchIndex]);
      if (!this.chapter) {
        logger.warn(`Chapitre inconnu : ${chapterIds[batchIndex]}, ignore.`);
        continue;
      }

      this.paragraphs = this.paragraphRepo.listByChapter(this.chapter.id);
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

      this.emitProgress({
        jobId: this.job.id,
        projectId: this.project.id,
        step: this.steps[0],
        totalSteps: this.steps.length,
        batchChapterIndex: batchIndex,
        batchTotalChapters: chapterIds.length,
      });

      await this.runFromIndex(0);

      if (this.job.status === "failed") {
        return;
      }
    }

    this.job.status = "completed";
    this.job.finishedAt = new Date().toISOString();
    this.jobRepo.updateJob(this.job);
    this.db.close();
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
    if (!step) {throw new Error(`Etape inconnue : ${stepId}`);}
    await this.runStep(step);
  }

  async retryFrom(stage: WorkflowStage): Promise<void> {
    const startIndex = STAGES.indexOf(stage);
    if (startIndex === -1) {throw new Error(`Stage inconnu : ${stage}`);}
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

  /** SDD §7.1 : Trouve le step complété avec le plus bas score et relance depuis ce point. */
  private async retryWeakestStep(): Promise<void> {
    const completed = this.steps.filter((s) => s.score !== undefined);
    if (completed.length === 0) {
      logger.warn("[Workflow] Aucun step complété, retry impossible");
      return;
    }
    // Trier par score croissant → le plus faible en premier
    completed.sort((a, b) => (a.score ?? 0) - (b.score ?? 0));
    const weakest = completed[0];
    logger.info(
      `[Workflow] Retry depuis le step le plus faible : ${weakest.stage} (score: ${weakest.score})`,
    );
    await this.retryFrom(weakest.stage);
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

      const input = await this.buildAgentInput(step.stage);
      step.inputSnapshot = input as unknown as Record<string, unknown>;
      this.jobRepo.updateStep(step);

      // SDD §22.2 : exécution dans un Worker thread si activé
      const useWorker = this.settings.get("useWorkerThreads");
      if (useWorker) {
        const agentConfig = {
          providerId: "ollama-default",
          model: this.settings.get("defaultModel"),
          temperature: 0.7,
        };
        const workerResult = await runAgentInWorker(
          step.stage,
          input,
          agentConfig,
        );
        if (workerResult.success) {
          output = workerResult.output as AgentOutput;
        } else {
          logger.warn(
            `[Workflow] Worker failed for ${step.stage}, fallback to direct execution: ${workerResult.error}`,
          );
          output = await agent.execute(input);
        }
      } else {
        output = await agent.execute(input);
      }

      // SDD §7.1 : Branching QA — décision après exécution du QA agent
      if (step.stage === "qa" && output) {
        const qualityThreshold = this.settings.get("qualityThreshold") ?? 80;
        const score = output.score ?? 0;

        if (score >= qualityThreshold) {
          // Qualité suffisante → continuer normalement
          logger.info(`[Workflow] QA score ${score} ≥ seuil ${qualityThreshold}, poursuite`);
        } else if (score >= qualityThreshold - 20) {
          // Score intermédiaire → retry du step le plus faible
          logger.warn(
            `[Workflow] QA score ${score} < ${qualityThreshold} mais ≥ ${qualityThreshold - 20}, retry step le plus faible`,
          );
          // Marquer le step comme complété avant retry
          step.status = "completed";
          step.score = score;
          step.outputSnapshot = output as unknown as Record<string, unknown>;
          step.finishedAt = new Date().toISOString();
          step.durationMs = Date.now() - startTime;
          this.jobRepo.updateStep(step);
          await this.retryWeakestStep();
          return output;
        } else {
          // Score trop bas → pause + événement
          logger.warn(
            `[Workflow] QA score ${score} < ${qualityThreshold - 20}, pause du workflow`,
          );
          step.status = "completed";
          step.score = score;
          step.outputSnapshot = output as unknown as Record<string, unknown>;
          step.finishedAt = new Date().toISOString();
          step.durationMs = Date.now() - startTime;
          this.jobRepo.updateStep(step);
          this.pause();
          this.emitQualityFailed?.({
            jobId: this.job.id,
            score,
            threshold: qualityThreshold,
          });
          return output;
        }
      }

      await this.applyAgentOutput(step.stage, output);

      step.status = "completed";
      step.score = output.score;
      step.outputSnapshot = output as unknown as Record<string, unknown>;

      // Stocker les embeddings après la traduction d'un chapitre
      if (
        step.stage === "translate" &&
        this.ragEngine &&
        this.settings.get("ragEnabled")
      ) {
        await this.storeEmbeddingsForChapter();
      }
    } catch (err) {
      logger.error(`Step ${step.stage} failed`, err);
      step.status = "failed";
      step.errorMessage = err instanceof Error ? err.message : String(err);
      step.finishedAt = new Date().toISOString();
      step.durationMs = Date.now() - startTime;
      this.jobRepo.updateStep(step);

      // SDD §22.6 : collecter les métriques même en cas d'échec
      this.profiler.collect(this.job.id, step.stage, {
        durationMs: step.durationMs,
      });

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
    step.tokensIn = output?.report
      ? (output.report as Record<string, unknown>)?.tokensIn as number
      : undefined;
    step.tokensOut = output?.report
      ? (output.report as Record<string, unknown>)?.tokensOut as number
      : undefined;
    this.jobRepo.updateStep(step);

    // SDD §22.6 : collecter les métriques de performance
    this.profiler.collect(this.job.id, step.stage, {
      durationMs: step.durationMs,
      tokensIn: step.tokensIn,
      tokensOut: step.tokensOut,
    });

    this.emitProgress({
      jobId: this.job.id,
      projectId: this.project.id,
      chapterId: this.chapter?.id,
      step,
      totalSteps: this.steps.length,
    });

    return output;
  }

  private async buildAgentInput(stage: WorkflowStage): Promise<AgentInput> {
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
      case "translate":
        // Enrichir le contexte avec les paragraphes similaires déjà traduits (RAG)
        if (this.ragEngine && this.settings.get("ragEnabled")) {
          try {
            const ragContext: Record<string, RagMatch[]> = {};
            for (const paragraph of this.paragraphs) {
              const matches = await this.ragEngine.findSimilar(
                paragraph.sourceText,
                this.project.id,
                3,
              );
              if (matches.length > 0) {
                ragContext[paragraph.id] = matches;
              }
            }
            if (Object.keys(ragContext).length > 0) {
              return {
                ...base,
                options: {
                  ...base.options,
                  ragContext,
                },
              };
            }
          } catch (err) {
            logger.warn(
              "RAG: impossible d'enrichir le contexte, poursuite sans RAG.",
              err,
            );
          }
        }
        return base;
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

  /**
   * Calcule et stocke les embeddings pour tous les paragraphes
   * traduits du chapitre courant.
   */
  private async storeEmbeddingsForChapter(): Promise<void> {
    if (!this.chapter || !this.ragEngine) {return;}

    for (const paragraph of this.paragraphs) {
      if (!paragraph.translatedText) {continue;}
      try {
        const embedding = await this.ragEngine.computeEmbedding(
          paragraph.sourceText,
        );
        this.ragEngine.storeEmbedding(this.chapter.id, paragraph.id, embedding);
      } catch (err) {
        logger.warn(
          `RAG: impossible de stocker l'embedding pour le paragraphe ${paragraph.id}`,
          err,
        );
      }
    }
  }
}

export class WorkflowEngine {
  private runners = new Map<string, WorkflowRunner>();
  /** SDD §7.9 : concurrence des jobs batch (défaut 1 pour Ollama local) */
  maxConcurrentJobs: number;
  /** SDD §7.4 : File d'attente pour limiter la concurrence */
  private queue: PQueue;

  /**
   * Profileur de performance partagé entre tous les runners.
   * Chaque runner collecte ses métriques sur cette instance unique.
   * SDD §22.6
   */
  readonly profiler: PerformanceProfiler;

  constructor(
    private settings: SettingsManager,
    private getMainWindow?: () => BrowserWindow | null,
  ) {
    this.maxConcurrentJobs = this.settings.get("maxConcurrentJobs");
    this.profiler = new PerformanceProfiler();
    this.queue = new PQueue({ concurrency: this.maxConcurrentJobs });
  }

  private emitProgress(payload: WorkflowProgress): void {
    const win = this.getMainWindow?.();
    if (win && !win.isDestroyed()) {
      win.webContents.send("workflow:progress", payload);
    }
  }

  private emitQualityFailed(payload: { jobId: string; score: number; threshold: number }): void {
    const win = this.getMainWindow?.();
    if (win && !win.isDestroyed()) {
      win.webContents.send("workflow:quality-failed", payload);
    }
  }

  /**
   * SDD §22.6 : Retourne le rapport de performance pour un job donné.
   */
  getProfilerReport(jobId: string): PerformanceMetrics[] {
    return this.profiler.getReport(jobId);
  }

  /**
   * SDD §22.6 : Exporte toutes les métriques de performance au format CSV.
   */
  exportProfilerCsv(): string {
    return this.profiler.exportCsv();
  }

  /** SDD §7.4 : Concurrency gate — file d'attente si maxConcurrentJobs atteint. */
  async start(projectPath: string, chapterId?: string): Promise<Job> {
    return this.queue.add(async () => {
      const runner = new WorkflowRunner(
        projectPath,
        this.settings,
        (p) => this.emitProgress(p),
        (p) => this.emitQualityFailed(p),
        this.profiler,
      );
      const job = await runner.start(chapterId);
      this.runners.set(job.id, runner);
      return job;
    });
  }

  /** SDD §7.4 : Concurrency gate — file d'attente si maxConcurrentJobs atteint. */
  async startBatch(projectPath: string, chapterIds: string[]): Promise<Job> {
    return this.queue.add(async () => {
      const runner = new WorkflowRunner(
        projectPath,
        this.settings,
        (p) => this.emitProgress(p),
        (p) => this.emitQualityFailed(p),
        this.profiler,
      );
      const job = await runner.startBatch(chapterIds);
      this.runners.set(job.id, runner);
      return job;
    });
  }

  /**
   * SDD §7.11 : Reprend un job batch interrompu au dernier chapitre non terminé.
   * @param projectPath Chemin du projet
   * @param job Job à reprendre (doit être de type batch avec chapterIds)
   */
  async resumeBatch(projectPath: string, job: Job): Promise<void> {
    return this.queue.add(async () => {
      const runner = new WorkflowRunner(
        projectPath,
        this.settings,
        (p) => this.emitProgress(p),
        (p) => this.emitQualityFailed(p),
        this.profiler,
      );
      await runner.resumeBatch(job);
      this.runners.set(job.id, runner);
    });
  }

  /**
   * SDD §7.11 : Reprend tous les jobs actifs (running/paused) au démarrage de l'application.
   * Parcourt les projets récents depuis les paramètres.
   */
  async resumeActiveJobs(): Promise<void> {
    const projectPaths = this.settings.get("recentProjects") as string[] | undefined;
    if (!projectPaths || projectPaths.length === 0) {
      logger.info("[WorkflowEngine] Aucun projet récent, reprise automatique ignorée");
      return;
    }

    let resumed = 0;
    for (const projectPath of projectPaths) {
      try {
        const db = createProjectDatabase(projectPath);
        runMigrations(db, path.join(__dirname, "../../db/migrations"));
        const jobRepo = new JobRepository(db);
        const activeJobs = jobRepo.listActive();
        db.close();

        for (const job of activeJobs) {
          if (job.type === "batch" && job.chapterIds && job.chapterIds.length > 0) {
            logger.info(
              `[WorkflowEngine] Reprise du job ${job.id} (${job.status}) pour ${projectPath}`,
            );
            await this.resumeBatch(projectPath, job);
            resumed++;
          }
        }
      } catch (err) {
        logger.warn(
          `[WorkflowEngine] Impossible de vérifier les jobs actifs pour ${projectPath}`,
          err,
        );
      }
    }

    if (resumed > 0) {
      logger.info(`[WorkflowEngine] ${resumed} job(s) repris automatiquement`);
    }
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

// === Worker threads — SDD §22.2 ===
//
// Préparation pour l'exécution d'agents CPU-bound dans des Worker threads.
// Actuellement, tous les agents s'exécutent de manière séquentielle dans le
// thread principal. Pour les agents coûteux (SplitAgent, ConsistencyChecker,
// ExportEngine), on pourra déléguer le travail à des Workers :
//
// 1. Créer un fichier worker wrapper : `src/main/workers/agent-worker.ts`
//    qui importe l'agent, reçoit les instructions via `parentPort.on('message')`,
//    exécute et renvoie le résultat.
//
// 2. Dans `WorkflowRunner`, remplacer l'appel direct à `agent.execute(input)`
//    par :
//    ```
//    const worker = new Worker('./workers/agent-worker.js');
//    worker.postMessage({ agentId: step.stage, input });
//    output = await new Promise((resolve, reject) => {
//      worker.on('message', resolve);
//      worker.on('error', reject);
//    });
//    ```
//
// 3. Gérer le pool de Workers via `maxConcurrentJobs` (SDD §7.9) :
//    limiter le nombre de Workers simultanés pour éviter la saturation CPU.
//
// 4. Attention : les Workers partagent la mémoire via `transferList` pour les
//    gros payloads (paragraphs). Utiliser `MessagePort` ou `SharedArrayBuffer`
//    si nécessaire.
//
// Non implémenté dans le MVP car :
// - Electron Worker threads nécessitent une configuration supplémentaire
//   (copie du bundle V8, gestion des chemins dans le contexte sandbox)
// - Le surcoût de sérialisation/deserialisation peut dépasser le gain pour
//   des payloads < 100 paragraphes
// - La priorité MVP est la fiabilité du pipeline séquentiel

import { EventEmitter } from "node:events";
import path from "node:path";
import PQueue from "p-queue";
import type { BrowserWindow } from "electron";
import type {
  AgentInput,
  AgentOutput,
  AiProvider,
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
import { PromptLoader } from "../services/prompts/PromptLoader.js";
import { LexiconEngine } from "../services/LexiconEngine.js";
import { TranslationMemoryEngine } from "../services/TranslationMemoryEngine.js";
import { ConsistencyChecker } from "../services/ConsistencyChecker.js";
import { QualityChecker } from "../services/QualityChecker.js";
import { ExportEngine } from "../services/ExportEngine.js";
import { CalibrationService } from "../services/CalibrationService.js";
import { HistoryRepository } from "../db/repositories/HistoryRepository.js";
import { SummaryRepository } from "../db/repositories/SummaryRepository.js";
import { RagEngine } from "../services/RagEngine.js";
import { SummarizerAgent } from "../services/agents/SummarizerAgent.js";
import { AiCache } from "../services/AiCache.js";
import { OllamaProvider } from "../services/providers/OllamaProvider.js";
import {
  PerformanceProfiler,
  type PerformanceMetrics,
} from "../services/PerformanceProfiler.js";
import { logger } from "../utils/logger.js";
import { runAgentInWorker } from "../workers/agent-worker.js";
import type { PluginHost } from "../plugins/PluginHost.js";

const STAGES: WorkflowStage[] = [
  "split",
  "pre_translate",
  "translate",
  "consistency",
  "lexicon",
  "grammar",
  "style",
  "polish",
  "review",  // v1.4 : boucle de révision pro (rapport de corrections ciblées)
  "revise",  // v1.4 : applique les corrections du ReviewReport
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
  private aiRouter: AiRouter;
  private jobRepo: JobRepository;
  private paragraphRepo: ParagraphRepository;
  private chapterRepo: ChapterRepository;
  private lexiconRepo: LexiconRepository;
  private summaryRepo: SummaryRepository;
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
    private pluginHost?: PluginHost,
  ) {
    super();
    this.profiler = profiler ?? new PerformanceProfiler();
    this.db = createProjectDatabase(projectPath);
    try {
      runMigrations(this.db, path.join(__dirname, "../../db/migrations"));

      const projectRepo = new ProjectRepository(this.db);
      const found = projectRepo.getByPath(projectPath);
      if (!found) {throw new Error(`Projet non trouve : ${projectPath}`);}
      this.project = found;
    } catch (err) {
      // Bug fix : si la migration ou la lookup projet échoue, on ferme la DB
      // ouverte ci-dessus pour éviter une fuite de connexion WAL.
      this.db.close();
      throw err;
    }

    this.sourceLanguage = this.project.sourceLanguage;
    this.targetLanguage = this.project.targetLanguage;

    this.jobRepo = new JobRepository(this.db);
    this.paragraphRepo = new ParagraphRepository(this.db);
    this.chapterRepo = new ChapterRepository(this.db);
    this.lexiconRepo = new LexiconRepository(this.db);
    this.summaryRepo = new SummaryRepository(this.db);

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

    // SDD §15 : câbler les plugins de providers (si PluginHost disponible)
    if (this.pluginHost) {
      aiRouter.setPluginProviderResolver((id: string) =>
        this.pluginHost!.getProvider(id) as unknown as AiProvider | undefined,
      );
    }

    // SDD §22.1 : activer le cache des réponses IA
    const aiCache = new AiCache(this.db);
    aiRouter.setCache(aiCache);

    // SDD §3.8 : configurer les coûts par modèle (depuis les settings)
    aiRouter.setModelCosts(this.settings.get("modelCosts"));

    // T5 fix : câbler le PromptLoader pour permettre les overrides de prompts
    // en DB (SDD §25). Les agents continuent d'importer leurs constantes TS ;
    // le PromptLoader est additif — AiRouter.chat() le consulte si défini.
    const promptLoader = new PromptLoader(this.db);
    aiRouter.setPromptLoader(promptLoader);

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
      // SDD §15 : permettre aux plugins de remplacer un agent built-in
      getPluginAgent: this.pluginHost
        ? (stage, config) => {
            const factoryFn = this.pluginHost!.getAgent(stage);
            // getAgent() retourne la factory enregistrée par le plugin via
            // context.registerAgent(stage, factory). On l'appelle avec le config.
            if (typeof factoryFn === "function") {
              const agent = (factoryFn as (cfg: unknown) => unknown)(config);
              return agent as import("../services/agents/Agent.js").Agent;
            }
            return undefined;
          }
        : undefined,
    });
    this.aiRouter = aiRouter;
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
      // Bug fix : fermer la DB sur échec (le runBatch normal ne l'atteint pas).
      this.db.close();
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
      // Bug fix : fermer la DB sur échec.
      this.db.close();
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

    this.steps = this.getActiveStages().map((stage, index) => ({
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
      // Bug fix : fermer la DB sur échec (le runSingle normal ne l'atteint pas).
      this.db.close();
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
        // Bug fix : fermer la DB sur early-return (cancel).
        this.db.close();
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
      this.steps = this.getActiveStages().map((stage, index) => ({
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
        // Bug fix : fermer la DB sur early-return (échec chapitre).
        this.db.close();
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
    const startIndex = this.getActiveStages().indexOf(stage);
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
      review: "Revisor",
      revise: "Correcteur",
      qa: "QA",
      export: "Export",
    };
    return names[stage];
  }

  /**
   * v1.4 — Retourne la liste des stages actifs selon les settings.
   * Permet de désactiver la boucle de révision pro (review/revise) si
   * `reviewLoopEnabled` est false (mode rapide).
   */
  private getActiveStages(): WorkflowStage[] {
    const reviewLoopEnabled = this.settings.get("reviewLoopEnabled") !== false;
    if (reviewLoopEnabled) {return STAGES;}
    return STAGES.filter((s) => s !== "review" && s !== "revise");
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
      // SDD §7.10 : timeout par étape (stepTimeoutMs). Si l'agent ne répond
      // pas dans le délai, on l'abandonne et on lève une erreur → catch ci-dessous
      // → step marqué failed, retry selon la politique existante.
      const timeoutMs = step.stepTimeoutMs ?? this.settings.get("stepTimeoutMs");
      const executeWithTimeout = async <T>(fn: () => Promise<T>): Promise<T> => {
        let timer: ReturnType<typeof setTimeout> | undefined;
        const timeoutPromise = new Promise<never>((_, reject) => {
          timer = setTimeout(
            () => reject(new Error(`Step ${step.stage} timed out after ${timeoutMs}ms`)),
            timeoutMs,
          );
        });
        try {
          return await Promise.race([fn(), timeoutPromise]);
        } finally {
          if (timer) {clearTimeout(timer);}
        }
      };

      if (useWorker) {
        const agentConfig = {
          providerId: "ollama-default",
          model: this.settings.get("defaultModel"),
          temperature: 0.7,
        };
        const workerResult = await executeWithTimeout(() =>
          runAgentInWorker(step.stage, input, agentConfig),
        );
        if (workerResult.success) {
          output = workerResult.output as AgentOutput;
        } else {
          logger.warn(
            `[Workflow] Worker failed for ${step.stage}, fallback to direct execution: ${workerResult.error}`,
          );
          output = await executeWithTimeout(() => agent.execute(input));
        }
      } else {
        output = await executeWithTimeout(() => agent.execute(input));
      }

      // SDD §8.13 : valider la sortie de l'agent si un outputSchema est défini
      if (output && agent.outputSchema) {
        try {
          output = agent.validateOutput(output);
        } catch (validationErr) {
          logger.warn(
            `[Workflow] Agent ${step.stage} output failed Zod validation, using raw output`,
            { error: (validationErr as Error).message },
          );
          // Conserver la sortie brute comme fallback
        }
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

      // v1.4 SDD §7.13 : Summarizer transverse après l'export du chapitre.
      // Maintient un NovelSummary injecté dans translate/style/polish des
      // chapitres suivants → cohérence cross-chapitre.
      if (step.stage === "export" && this.settings.get("summarizerEnabled") !== false) {
        await this.summarizeChapter();
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

    // SDD §3.8 : accumuler le coût estimé (providers cloud uniquement)
    if (step.tokensIn || step.tokensOut) {
      const model = this.settings.get("defaultModel");
      const stepCost = this.aiRouter.estimateCost(
        model,
        step.tokensIn ?? 0,
        step.tokensOut ?? 0,
      );
      if (stepCost > 0) {
        this.job.costUsd = (this.job.costUsd ?? 0) + stepCost;
        this.jobRepo.updateJob(this.job);
      }
    }

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
    // v1.4 SDD §7.13 : injecter le NovelSummary pour la cohérence cross-chapitre
    const novelSummaryRow = this.summaryRepo.getNovelSummary(this.project.id);
    const novelSummary = novelSummaryRow?.summary;
    const base: AgentInput = {
      projectId: this.project.id,
      chapterId: this.chapter?.id,
      paragraphs: this.paragraphs,
      lexicon,
      options: {
        sourceLanguage: this.sourceLanguage,
        targetLanguage: this.targetLanguage,
        title: this.chapter?.title ?? "Export",
        novelSummary,
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
      case "review":
        return {
          ...base,
          text: this.paragraphs.map((p) => p.translatedText ?? "").join("\n\n"),
          paragraphs: this.paragraphs, // review a besoin des paragraphes source+cible
        };
      case "revise": {
        // v1.4 : injecter le ReviewReport du stage précédent (review)
        const reviewStep = this.steps.find((s) => s.stage === "review");
        const reviewReport = reviewStep?.outputSnapshot?.report as
          | import("@shared/types/index.js").ReviewReport
          | undefined;
        return {
          ...base,
          text: this.paragraphs.map((p) => p.translatedText ?? "").join("\n\n"),
          paragraphs: undefined,
          options: {
            ...base.options,
            reviewReport,
          },
        };
      }
      case "export":
        return {
          ...base,
          options: {
            ...base.options,
            format: "markdown",
            outputPath: path.join(this.project.path, "exports"),
          },
        };
      case "qa": {
        // T8 fix : injecter le ConsistencyReport du stage précédent pour que
        // QualityChecker utilise le vrai score de cohérence (pas un fallback 90).
        const consistencyStep = this.steps.find(
          (s) => s.stage === "consistency",
        );
        const consistencyReport = consistencyStep?.outputSnapshot?.report as
          | import("@shared/types/index.js").ConsistencyReport
          | undefined;
        if (consistencyReport) {
          return {
            ...base,
            options: {
              ...base.options,
              consistencyReport,
            },
          };
        }
        return base;
      }
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
      ["lexicon", "grammar", "style", "polish", "revise"].includes(stage)
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
   *
   * T13 fix : utilise le batch computeEmbeddings/storeEmbeddings (1 appel
   * Ollama /api/embed pour tout le chapitre) au lieu de N appels paragraphe
   * par paragraphe. Passe de O(N) appels réseau à O(1) par chapitre.
   */
  private async storeEmbeddingsForChapter(): Promise<void> {
    if (!this.chapter || !this.ragEngine) {return;}

    // Collecter les paragraphes traduits (sourceText pour l'embedding)
    const toEmbed = this.paragraphs
      .filter((p) => p.translatedText)
      .map((p) => ({ paragraph: p, sourceText: p.sourceText }));

    if (toEmbed.length === 0) {return;}

    try {
      // T13 fix : un seul appel batch Ollama pour tout le chapitre
      const embeddings = await this.ragEngine.computeEmbeddings(
        toEmbed.map((e) => e.sourceText),
      );

      const entries = toEmbed.map((e, i) => ({
        chapterId: this.chapter!.id,
        paragraphId: e.paragraph.id,
        embedding: embeddings[i],
      }));
      this.ragEngine.storeEmbeddings(entries);
    } catch (err) {
      logger.warn(
        `RAG: échec du batch d'embeddings pour le chapitre ${this.chapter.id}, fallback per-paragraph`,
        err,
      );
      // Fallback : calculer un par un (ancien comportement)
      for (const { paragraph } of toEmbed) {
        try {
          const embedding = await this.ragEngine.computeEmbedding(
            paragraph.sourceText,
          );
          this.ragEngine.storeEmbedding(this.chapter.id, paragraph.id, embedding);
        } catch (e) {
          logger.warn(
            `RAG: impossible de stocker l'embedding pour le paragraphe ${paragraph.id}`,
            e,
          );
        }
      }
    }
  }

  /**
   * v1.4 SDD §7.13 — Produit un résumé du chapitre courant et met à jour le
   * résumé incrémental du roman (NovelSummary). Le NovelSummary est injecté
   * dans le contexte des stages translate/style/polish/review des chapitres
   * suivants → cohérence cross-chapitre (noms, intrigue, ton).
   *
   * Agent transverse : appelé après l'export réussi d'un chapitre.
   */
  private async summarizeChapter(): Promise<void> {
    if (!this.chapter) {return;}

    try {
      // Charger le résumé précédent du roman (si chapters antérieurs traités)
      const existing = this.summaryRepo.getNovelSummary(this.project.id);
      const previousSummary = existing?.summary;

      const agent = new SummarizerAgent(
        {
          providerId: "ollama-default",
          model: this.settings.get("defaultModel"),
        },
        this.aiRouter,
      );

      const output = await agent.execute({
        projectId: this.project.id,
        chapterId: this.chapter.id,
        paragraphs: this.paragraphs,
        options: { novelSummary: previousSummary },
      });

      const chapterSummary = output.metadata?.chapterSummary as string | undefined;
      const updatedNovelSummary = output.metadata?.novelSummary as string | undefined;

      // Persister le résumé du chapitre
      if (chapterSummary && chapterSummary.trim().length > 0) {
        this.summaryRepo.upsertChapterSummary({
          chapterId: this.chapter.id,
          projectId: this.project.id,
          summary: chapterSummary,
          tokenCount: undefined,
        });
      }

      // Persister le résumé mis à jour du roman
      if (updatedNovelSummary && updatedNovelSummary.trim().length > 0) {
        this.summaryRepo.upsertNovelSummary(this.project.id, updatedNovelSummary);
        logger.info(
          `[Summarizer] Résumé du roman mis à jour pour le projet ${this.project.id}`,
        );
      }
    } catch (err) {
      // Non-bloquant : la cohérence cross-chapitre est un plus, pas une exigence
      logger.warn(
        `[Summarizer] Échec de la synthèse pour le chapitre ${this.chapter.id}`,
        err,
      );
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

  /**
   * SDD §15 : PluginHost partagé, injecté dans chaque WorkflowRunner.
   * Défini après construction (le PluginHost est créé plus tard dans index.ts).
   */
  private pluginHost?: PluginHost;

  constructor(
    private settings: SettingsManager,
    private getMainWindow?: () => BrowserWindow | null,
  ) {
    this.maxConcurrentJobs = this.settings.get("maxConcurrentJobs");
    this.profiler = new PerformanceProfiler();
    this.queue = new PQueue({ concurrency: this.maxConcurrentJobs });
  }

  /**
   * SDD §15 : Connecte le PluginHost au WorkflowEngine.
   * À appeler après l'initialisation du PluginHost (index.ts) pour activer
   * l'extensibilité d'agents/providers par plugin.
   */
  setPluginHost(pluginHost: PluginHost): void {
    this.pluginHost = pluginHost;
    logger.info("[WorkflowEngine] PluginHost connecté — extensibilité agents/providers active");
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
        this.pluginHost,
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
        this.pluginHost,
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
        this.pluginHost,
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
    let cleaned = 0;
    for (const projectPath of projectPaths) {
      try {
        const db = createProjectDatabase(projectPath);
        runMigrations(db, path.join(__dirname, "../../db/migrations"));
        const jobRepo = new JobRepository(db);
        const activeJobs = jobRepo.listActive();

        for (const job of activeJobs) {
          if (job.type === "batch" && job.chapterIds && job.chapterIds.length > 0) {
            // Les jobs batch peuvent être repris via batchChapterIndex
            logger.info(
              `[WorkflowEngine] Reprise du job batch ${job.id} (${job.status}) pour ${projectPath}`,
            );
            await this.resumeBatch(projectPath, job);
            resumed++;
          } else {
            // T4A fix : les jobs single abandonnés ne peuvent pas être repris
            // (pas assez d'état persisté). On les marque failed proprement
            // pour éviter qu'ils restent bloqués en "running" éternellement.
            logger.warn(
              `[WorkflowEngine] Job single ${job.id} (${job.status}) interrompu — marqué comme failed`,
            );
            jobRepo.updateJob({
              ...job,
              status: "failed",
              errorMessage: "Interrompu (redémarrage de l'application)",
              finishedAt: new Date().toISOString(),
            });
            cleaned++;
          }
        }
        db.close();
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
    if (cleaned > 0) {
      logger.info(
        `[WorkflowEngine] ${cleaned} job(s) single abandonné(s) marqué(s) failed`,
      );
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
// Implémentation active : les agents s'exécutent dans un Worker thread lorsque
// `useWorkerThreads` est activé (défaut: true, cf. schemas/index.ts). Le worker
// (`src/main/workers/agent-worker.ts`) reçoit { stage, config, input } via
// postMessage, instancie l'agent via AgentFactory et renvoie l'output.
//
// En cas d'échec du worker (erreur de sérialisation, chemin de module, etc.),
// le runner bascule en silencieux vers une exécution directe dans le thread
// principal (cf. runStep, fallback sur executeWithTimeout(() => agent.execute)).
//
// Historique : le bug T14 (imports PascalCase mal résolus depuis le worker)
// a été corrigé — les chemins d'import respectent maintenant la casse exacte
// des fichiers. Le présent commentaire remplace une note obsolète qui décrivait
// les Worker threads comme "non implémentés dans le MVP" alors qu'ils sont
// effectifs et activés par défaut.

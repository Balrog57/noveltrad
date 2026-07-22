// v3 — 2026-07-22 (REFACTOR_PLAN_V3.md Phase 1)
// Remplaçant simplifié du WorkflowRunner (managers/WorkflowEngine.ts).
//
// Pipeline séquentiel 4-stages, EXÉCUTION IN-THREAD (pas de worker_threads) :
//   SOURCE → translate → proofread → glossary → validate → FINAL
//
// Différences vs WorkflowRunner (l'ancien) :
//   - 4 stages au lieu de 12 (split/pre_translate/consistency/grammar/style/
//     polish/review/revise/qa/export supprimés ou fusionnés).
//   - In-thread : pas de runAgentInWorker (suppression des worker_threads en Phase 3).
//   - Pas de jobs table : la progression est en mémoire + events workflow:progress.
//   - Pas de QA auto-retry branching (QaBranchPolicy) : le validateur produit un
//     score, l'utilisateur décide de relancer si besoin (décision v3).
//   - Pas de pause/resume persistant : cancel only. (La reprise = re-run, on
//     saute les paragraphes déjà "translated".)
//   - Summarizer conservé (transverse) : déclenché après "validate" au lieu de
//     "export", gated par summarizerEnabled.
//
// La DB setup (createProjectDatabase + runMigrations + repos + AiRouter +
// OllamaProvider + AgentFactory) est reproductible du WorkflowRunner pour
// garantir le même comportement de fondation.

import type {
  AgentInput,
  AgentOutput,
  Chapter,
  Paragraph,
  Project,
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
import { SummaryRepository } from "../db/repositories/SummaryRepository.js";
import { AgentFactory } from "../services/agents/AgentFactory.js";
import { AiRouter } from "../services/AiRouter.js";
import { PromptLoader } from "../services/prompts/PromptLoader.js";
import { LexiconEngine } from "../services/LexiconEngine.js";
import { TranslationMemoryEngine } from "../services/TranslationMemoryEngine.js";
import { ConsistencyChecker } from "../services/ConsistencyChecker.js";
import { QualityChecker } from "../services/QualityChecker.js";
import { SummarizerAgent } from "../services/agents/SummarizerAgent.js";
import { AiCache } from "../services/AiCache.js";
import { OllamaProvider } from "../services/providers/OllamaProvider.js";
import type { AgentConfig } from "../services/agents/Agent.js";
import { logger } from "../utils/logger.js";

/** Les 4 stages du pipeline v3, dans l'ordre. */
export const SIMPLE_STAGES: WorkflowStage[] = [
  "translate",
  "proofread",
  "glossary",
  "validate",
];

/** Payload de progression (subset de l'ancien WorkflowProgress, sans Step lourd). */
export interface SimpleProgress {
  jobId: string;
  projectId: string;
  chapterId?: string;
  stage: WorkflowStage;
  stageIndex: number;
  totalStages: number;
  /** Index du chapitre en cours dans un batch (0-based). */
  batchChapterIndex?: number;
  batchTotalChapters?: number;
  /** Statut du stage : "running" | "completed" | "failed". */
  status: "running" | "completed" | "failed";
}

/**
 * Runner v3 : exécute le pipeline 4-stages sur un chapitre (ou un batch).
 *
 * Usage depuis ipc/handlers/workflow.ts (Phase 3) :
 *   const runner = new SimpleWorkflowRunner(projectPath, settings, getMainWindow);
 *   await runner.runChapter(chapterId);
 *   await runner.runBatch(chapterIds);
 */
export class SimpleWorkflowRunner {
  private db: ProjectDatabase;
  private project: Project;
  private chapter?: Chapter;
  private paragraphs: Paragraph[] = [];
  private factory: AgentFactory;
  private aiRouter: AiRouter;
  private paragraphRepo: ParagraphRepository;
  private chapterRepo: ChapterRepository;
  private lexiconRepo: LexiconRepository;
  private summaryRepo: SummaryRepository;
  private settings: SettingsManager;
  private disposed = false;
  /** jobId du run courant (pour cancel). */
  private currentJobId?: string;
  private cancelled = false;

  constructor(
    projectPath: string,
    settings: SettingsManager,
    private emitProgress?: (payload: SimpleProgress) => void,
  ) {
    this.settings = settings;
    this.db = createProjectDatabase(projectPath);
    try {
      runMigrations(this.db);

      const projectRepo = new ProjectRepository(this.db);
      const found = projectRepo.getByPath(projectPath);
      if (!found) {
        throw new Error(`Projet non trouvé : ${projectPath}`);
      }
      this.project = found;

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

      const aiCache = new AiCache(this.db);
      aiRouter.setCache(aiCache);
      aiRouter.setModelCosts(this.settings.get("modelCosts"));

      const promptLoader = new PromptLoader(this.db);
      aiRouter.setPromptLoader(promptLoader);

      const lexiconEngine = new LexiconEngine();
      const tmEngine = new TranslationMemoryEngine();
      tmEngine.setDatabase(this.db);

      this.factory = new AgentFactory({
        aiRouter,
        lexiconEngine,
        tmEngine,
        consistencyChecker: new ConsistencyChecker(),
        qualityChecker: new QualityChecker(),
      });
      this.aiRouter = aiRouter;
    } catch (err) {
      this.dispose();
      throw err;
    }
  }

  /** Fermeture idempotente de la DB (cf. WorkflowRunner.dispose). */
  dispose(): void {
    if (this.disposed) {
      return;
    }
    this.disposed = true;
    try {
      this.db.close();
    } catch {
      // DB peut déjà être fermée — idempotence.
    }
  }

  /** Demande l'annulation du run courant. Le stage en cours se termine, les suivants sont sautés. */
  cancel(): void {
    this.cancelled = true;
  }

  /** Exécute le pipeline sur un chapitre unique. */
  async runChapter(jobId: string, chapterId: string): Promise<void> {
    this.currentJobId = jobId;
    this.cancelled = false;

    const chapter = this.chapterRepo.getById(chapterId);
    if (!chapter) {
      throw new Error(`Chapitre non trouvé : ${chapterId}`);
    }
    this.chapter = chapter;
    this.paragraphs = this.paragraphRepo.listByChapter(chapterId);

    await this.runPipeline(jobId);
  }

  /** Exécute le pipeline sur plusieurs chapitres, séquentiellement. */
  async runBatch(jobId: string, chapterIds: string[]): Promise<void> {
    if (chapterIds.length === 0) {
      throw new Error("Aucun chapitre sélectionné");
    }
    this.currentJobId = jobId;
    this.cancelled = false;

    for (let i = 0; i < chapterIds.length; i++) {
      if (this.cancelled) {
        logger.info(`[SimpleWorkflowRunner] Batch annulé au chapitre ${i}/${chapterIds.length}`);
        return;
      }

      const chapterId = chapterIds[i];
      const chapter = this.chapterRepo.getById(chapterId);
      if (!chapter) {
        logger.warn(`[SimpleWorkflowRunner] Chapitre ${chapterId} introuvable, ignoré`);
        continue;
      }
      this.chapter = chapter;
      this.paragraphs = this.paragraphRepo.listByChapter(chapterId);

      await this.runPipeline(jobId, i, chapterIds.length);
    }
  }

  /**
   * Cœur du pipeline : itère les 4 stages, marshal l'input/output, persiste.
   */
  private async runPipeline(
    jobId: string,
    batchChapterIndex?: number,
    batchTotalChapters?: number,
  ): Promise<void> {
    const config = this.agentConfig();

    for (let i = 0; i < SIMPLE_STAGES.length; i++) {
      if (this.cancelled) {
        return;
      }

      const stage = SIMPLE_STAGES[i];
      const emitBase = {
        jobId,
        projectId: this.project.id,
        chapterId: this.chapter?.id,
        stage,
        stageIndex: i,
        totalStages: SIMPLE_STAGES.length,
        batchChapterIndex,
        batchTotalChapters,
      };

      this.emitProgress?.({ ...emitBase, status: "running" });

      try {
        const agent = this.factory.create(stage, config);
        const input = await this.buildAgentInput(stage);
        const output = await agent.execute(input);
        this.applyAgentOutput(stage, output);

        this.emitProgress?.({ ...emitBase, status: "completed" });
      } catch (err) {
        logger.error(`[SimpleWorkflowRunner] Stage ${stage} failed`, err);
        this.emitProgress?.({ ...emitBase, status: "failed" });
        throw err;
      }
    }

    // Pipeline terminé : marquer le chapitre, puis Summarizer (transverse).
    if (this.chapter) {
      this.chapterRepo.updateStatus(this.chapter.id, "completed");
      if (this.settings.get("summarizerEnabled") !== false) {
        await this.summarizeChapter();
      }
    }
  }

  /**
   * Construit l'AgentInput pour un stage donné. Reproduit la logique de
   * WorkflowEngine.buildAgentInput, simplifiée pour les 4 stages v3.
   */
  private async buildAgentInput(stage: WorkflowStage): Promise<AgentInput> {
    const lexicon = this.lexiconRepo.listByProject(this.project.id);
    const novelSummaryRow = this.summaryRepo.getNovelSummary(this.project.id);
    const novelSummary = novelSummaryRow?.summary;

    const base: AgentInput = {
      projectId: this.project.id,
      chapterId: this.chapter?.id,
      paragraphs: this.paragraphs,
      lexicon,
      options: {
        sourceLanguage: this.project.sourceLanguage,
        targetLanguage: this.project.targetLanguage,
        title: this.chapter?.title ?? "Export",
        novelSummary,
      },
    };

    switch (stage) {
      case "translate":
        // Pas de RAG en v3 (RagEngine supprimé). TM matches gérés par TranslateAgent.
        return base;
      case "proofread":
      case "glossary":
        return {
          ...base,
          text: this.paragraphs.map((p) => p.translatedText ?? "").join("\n\n"),
          // Validator a besoin des paragraphes source+cible ; proofread/glossary
          // travaillent sur le texte agrégé. On garde paragraphs pour Validator.
          paragraphs: stage === "glossary" ? undefined : this.paragraphs,
        };
      case "validate":
        // Validator (fusion consistency+qa) a besoin des paragraphes source+cible.
        return {
          ...base,
          paragraphs: this.paragraphs,
        };
      default:
        return base;
    }
  }

  /**
   * Applique la sortie d'un agent sur l'état des paragraphes et persiste.
   * Reproduit WorkflowEngine.applyAgentOutput, simplifié.
   */
  private applyAgentOutput(stage: WorkflowStage, output: AgentOutput): void {
    // translate : retourne des paragraphes (avec translatedText).
    if (stage === "translate" && output.paragraphs) {
      this.paragraphs = output.paragraphs.map((p, index) => ({
        ...p,
        chapterId: this.chapter?.id ?? p.chapterId,
        indexInChapter: p.indexInChapter ?? index + 1,
      }));
      if (this.chapter) {
        this.paragraphRepo.upsertMany(this.chapter.id, this.paragraphs);
      }
      return;
    }

    // proofread / glossary : retournent du texte agrégé à re-découper en paragraphes.
    if ((stage === "proofread" || stage === "glossary") && output.text) {
      const parts = output.text.split(/\n\n+/);
      this.paragraphs = this.paragraphs.map((p, i) => ({
        ...p,
        translatedText: parts[i] ?? p.translatedText ?? "",
      }));
      if (this.chapter) {
        this.paragraphRepo.upsertMany(this.chapter.id, this.paragraphs);
      }
      return;
    }

    // validate : retourne un report (pas de mutation du texte).
  }

  /** Summarizer transverse : résumé chapitre + mise à jour du résumé roman. */
  private async summarizeChapter(): Promise<void> {
    if (!this.chapter) {
      return;
    }
    try {
      const existing = this.summaryRepo.getNovelSummary(this.project.id);
      const previousSummary = existing?.summary;
      const agent = new SummarizerAgent(this.agentConfig(), this.aiRouter);
      const output = await agent.execute({
        projectId: this.project.id,
        chapterId: this.chapter.id,
        paragraphs: this.paragraphs,
        options: { novelSummary: previousSummary },
      });
      const chapterSummary = output.metadata?.chapterSummary as
        | string
        | undefined;
      const novelSummary = output.metadata?.novelSummary as string | undefined;
      if (chapterSummary) {
        this.summaryRepo.upsertChapterSummary({
          chapterId: this.chapter.id,
          projectId: this.project.id,
          summary: chapterSummary,
        });
      }
      if (novelSummary) {
        this.summaryRepo.upsertNovelSummary(this.project.id, novelSummary);
      }
    } catch (err) {
      // Le summarizer est best-effort : ne fait pas échouer le pipeline.
      logger.warn("[SimpleWorkflowRunner] Summarizer failed (non-fatal)", {
        error: (err as Error).message,
      });
    }
  }

  /** Construit l'AgentConfig depuis les settings. */
  private agentConfig(): AgentConfig {
    return {
      providerId: "ollama-default",
      model: this.settings.get("defaultModel"),
      temperature: 0.7,
    };
  }
}

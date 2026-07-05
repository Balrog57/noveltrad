import type { Agent, AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  QualityReport,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import type { QualityChecker } from "../QualityChecker.js";
import type { CalibrationService } from "../CalibrationService.js";
import {
  QA_SYSTEM_PROMPT,
  buildQaUserPrompt,
} from "../prompts/qa.system.js";
import { logger } from "../../utils/logger.js";

/** Dimensions de qualité calibrables (exclut globalScore et comments) */
const CALIBRATABLE_DIMENSIONS = [
  "consistency",
  "grammar",
  "fluency",
  "style",
  "lexicon",
  "hallucination",
  "length",
  "dialogue",
] as const;

export class QaAgent implements Agent {
  readonly id = "qa";
  readonly name = "QA";
  readonly stage = "qa";

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
    private qualityChecker: QualityChecker,
    /** SDD §12.5 : service de calibration optionnel */
    private calibrationService?: CalibrationService,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const sourceText = paragraphs.map((p) => p.sourceText).join("\n\n");
    const translatedText = paragraphs
      .map((p) => p.translatedText ?? "")
      .join("\n\n");
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";

    // Phase 1 : LLM evaluation (primary)
    let report: QualityReport;
    let llmAvailable = false;

    const fallbackEvaluate = (): Promise<QualityReport> =>
      this.qualityChecker.evaluate(
        sourceText,
        translatedText,
        input.lexicon ?? [],
      );

    try {
      const userPrompt = buildQaUserPrompt({
        sourceText,
        translatedText,
        targetLanguage,
      });

      const response = await this.aiRouter.chat(
        this.config.providerId,
        [
          { role: "system", content: QA_SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        { jsonMode: true },
      );

      const parsed = this.aiRouter.tryParseJson(response);
      if (parsed && typeof parsed === "object") {
        const obj = parsed as Record<string, unknown>;
        report = {
          consistency: typeof obj.consistency === "number" ? obj.consistency : 50,
          grammar: typeof obj.grammar === "number" ? obj.grammar : 50,
          fluency: typeof obj.fluency === "number" ? obj.fluency : 50,
          style: typeof obj.style === "number" ? obj.style : 50,
          lexicon: typeof obj.lexicon === "number" ? obj.lexicon : 50,
          hallucination: typeof obj.hallucination === "number" ? obj.hallucination : 50,
          length: typeof obj.length === "number" ? obj.length : 50,
          dialogue: typeof obj.dialogue === "number" ? obj.dialogue : 50,
          globalScore: typeof obj.globalScore === "number" ? obj.globalScore : 50,
          comments: String(obj.comments ?? ""),
        };
        llmAvailable = true;
      } else {
        // Phase 2 : Fallback to heuristic evaluation
        report = await fallbackEvaluate();
      }
    } catch (err) {
      logger.warn(
        "[QaAgent] LLM evaluation failed, falling back to heuristic QualityChecker",
        { error: (err as Error).message },
      );
      // Phase 2 : Fallback to heuristic evaluation
      report = await fallbackEvaluate();
    }

    // SDD §12.5 : appliquer la calibration avant le calcul du globalScore
    const calibratedReport = this.applyCalibration(report);

    return { report: calibratedReport, score: calibratedReport.globalScore };
  }

  /**
   * Applique la calibration à chaque dimension du rapport de qualité,
   * puis recalcule le globalScore à partir des scores calibrés.
   *
   * Si aucun CalibrationService n'est fourni, retourne le rapport tel quel.
   */
  private applyCalibration(report: QualityReport): QualityReport {
    if (!this.calibrationService) {return report;}

    const model = this.config.model;
    const calibrated: QualityReport = { ...report };

    for (const dim of CALIBRATABLE_DIMENSIONS) {
      const raw = report[dim];
      calibrated[dim] = this.calibrationService.calibrateScore(raw, model, dim);
    }

    // Recalculer le globalScore avec les scores calibrés (mêmes pondérations que QualityChecker)
    calibrated.globalScore = Math.round(
      calibrated.consistency * 0.25 +
        calibrated.grammar * 0.15 +
        calibrated.fluency * 0.2 +
        calibrated.style * 0.15 +
        calibrated.lexicon * 0.15 +
        calibrated.hallucination * 0.05 +
        calibrated.length * 0.03 +
        calibrated.dialogue * 0.02,
    );

    return calibrated;
  }
}

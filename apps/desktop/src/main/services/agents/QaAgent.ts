import type { Agent, AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  QualityReport,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import type { QualityChecker } from "../QualityChecker.js";
import type { CalibrationService } from "../CalibrationService.js";

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

type CalibratableDimension = (typeof CALIBRATABLE_DIMENSIONS)[number];

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

    const report = await this.qualityChecker.evaluate(
      sourceText,
      translatedText,
      input.lexicon ?? [],
    );

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
    if (!this.calibrationService) return report;

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

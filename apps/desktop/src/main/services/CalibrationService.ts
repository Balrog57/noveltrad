import type { ProjectDatabase } from "../db/connection.js";
import type { ModelCalibration } from "@shared/types/index.js";

/**
 * SDD §12.5 : Service de calibration des scores de qualité.
 *
 * Permet de recalibrer les scores heuristiques produits par QualityChecker
 * en fonction du modèle de traduction utilisé. La calibration est une
 * régression linéaire simple : `score_calibré = raw * slope + offset`.
 *
 * Le jeu de référence est constitué de 20 chapitres annotés manuellement.
 * On recalibre quand le modèle change ou tous les 100 chapitres.
 *
 * Bornes : le score calibré est toujours dans [0, 100].
 */
export class CalibrationService {
  /** Dimensions de qualité calibrables (alignées sur QualityReport) */
  static readonly DIMENSIONS = [
    "consistency",
    "grammar",
    "fluency",
    "style",
    "lexicon",
    "hallucination",
    "length",
    "dialogue",
  ] as const;

  constructor(private db: ProjectDatabase) {}

  /**
   * Calibre un score brut en appliquant la régression linéaire
   * `score_calibré = raw * slope + offset`, borné dans [0, 100].
   *
   * Si aucune calibration n'existe pour (model, dimension), retourne le
   * score brut borné dans [0, 100] (slope=1, offset=0 par défaut).
   *
   * SDD §12.5 : `Math.min(100, Math.max(0, Math.round(raw * slope + offset)))`
   */
  calibrateScore(raw: number, model: string, dimension: string): number {
    const calibration = this.loadCalibration(model, dimension);
    const slope = calibration?.slope ?? 1;
    const offset = calibration?.offset ?? 0;
    return Math.min(100, Math.max(0, Math.round(raw * slope + offset)));
  }

  /**
   * Charge la calibration pour un couple (model, dimension).
   * Retourne `undefined` si aucune calibration n'est stockée.
   */
  loadCalibration(
    model: string,
    dimension: string,
  ): ModelCalibration | undefined {
    const row = this.db
      .prepare(
        `SELECT model, dimension, slope, offset, sample_count AS sampleCount, updated_at AS updatedAt
         FROM model_calibrations WHERE model = ? AND dimension = ?`,
      )
      .get([model, dimension]) as
      | {
          model: string;
          dimension: string;
          slope: number;
          offset: number;
          sampleCount: number;
          updatedAt: string;
        }
      | undefined;

    if (!row) {return undefined;}
    return {
      model: row.model,
      dimension: row.dimension,
      slope: row.slope,
      offset: row.offset,
      sampleCount: row.sampleCount,
      updatedAt: row.updatedAt,
    };
  }

  /**
   * Stocke (ou met à jour) la calibration pour un couple (model, dimension).
   * Utilise un UPSERT (INSERT OR REPLACE) car la clé primaire est (model, dimension).
   */
  storeCalibration(calibration: ModelCalibration): void {
    this.db
      .prepare(
        `INSERT OR REPLACE INTO model_calibrations
         (model, dimension, slope, offset, sample_count, updated_at)
         VALUES (?, ?, ?, ?, ?, ?)`,
      )
      .run([
        calibration.model,
        calibration.dimension,
        calibration.slope,
        calibration.offset,
        calibration.sampleCount,
        calibration.updatedAt,
      ]);
  }

  /**
   * Calcule les paramètres de régression linéaire (slope, offset) à partir
   * d'un jeu de référence de paires (score brut, score annoté).
   *
   * Utilise la méthode des moindres carrés :
   *   slope = Σ((x - x̄)(y - ȳ)) / Σ((x - x̄)²)
   *   offset = ȳ - slope * x̄
   *
   * Si le dénominateur est nul (tous les scores bruts identiques) ou si
   * moins de 2 échantillons, retourne slope=1, offset=0 (pas de calibration).
   *
   * @param samples Paires (rawScore, annotatedScore)
   * @returns Paramètres de calibration (slope, offset, sampleCount)
   */
  computeRegression(samples: Array<{ raw: number; annotated: number }>): {
    slope: number;
    offset: number;
    sampleCount: number;
  } {
    const n = samples.length;
    if (n < 2) {
      return { slope: 1, offset: 0, sampleCount: n };
    }

    const sumX = samples.reduce((acc, s) => acc + s.raw, 0);
    const sumY = samples.reduce((acc, s) => acc + s.annotated, 0);
    const meanX = sumX / n;
    const meanY = sumY / n;

    let numerator = 0;
    let denominator = 0;
    for (const s of samples) {
      const dx = s.raw - meanX;
      numerator += dx * (s.annotated - meanY);
      denominator += dx * dx;
    }

    if (denominator === 0) {
      return { slope: 1, offset: 0, sampleCount: n };
    }

    const slope = numerator / denominator;
    const offset = meanY - slope * meanX;
    return { slope, offset, sampleCount: n };
  }

  /**
   * Calibre toutes les dimensions pour un modèle donné à partir d'un jeu
   * de référence. Stocke les calibrations calculées en base.
   *
   * @param model Nom du modèle (ex: "qwen3.5:9b")
   * @param referenceData Map dimension -> paires (raw, annotated)
   */
  calibrateFromReference(
    model: string,
    referenceData: Record<string, Array<{ raw: number; annotated: number }>>,
  ): void {
    const updatedAt = new Date().toISOString();
    for (const [dimension, samples] of Object.entries(referenceData)) {
      const { slope, offset, sampleCount } = this.computeRegression(samples);
      this.storeCalibration({
        model,
        dimension,
        slope,
        offset,
        sampleCount,
        updatedAt,
      });
    }
  }

  /**
   * Indique s'il faut recalibrer le modèle.
   * SDD §12.5 : recalibrer quand le modèle change ou tous les 100 chapitres.
   *
   * @param model Nom du modèle
   * @param chaptersProcessed Nombre de chapitres traités depuis la dernière calibration
   * @returns `true` s'il faut recalibrer
   */
  shouldRecalibrate(model: string, chaptersProcessed: number): boolean {
    // Recalibrer tous les 100 chapitres
    if (chaptersProcessed > 0 && chaptersProcessed % 100 === 0) {
      return true;
    }
    // Recalibrer si aucune calibration n'existe pour ce modèle
    const hasCalibration = CalibrationService.DIMENSIONS.some(
      (dim) => this.loadCalibration(model, dim) !== undefined,
    );
    return !hasCalibration;
  }
}

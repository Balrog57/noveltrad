import { describe, it, expect, beforeEach } from "vitest";
import { CalibrationService } from "../../src/main/services/CalibrationService";
import { HallucinationDetector } from "../../src/main/services/HallucinationDetector";
import {
  ConsistencyChecker,
  DEFAULT_TOLERANCES,
  DEFAULT_TOLERANCE,
} from "../../src/main/services/ConsistencyChecker";
import type { ModelCalibration } from "@shared/types/index.js";

// ── Mock DB SQLite pour CalibrationService ──

interface CalibrationRow {
  model: string;
  dimension: string;
  slope: number;
  offset: number;
  sample_count: number;
  updated_at: string;
}

class MockCalibrationDatabase {
  private rows: Map<string, CalibrationRow> = new Map();

  prepare(sql: string): {
    get: (params: unknown[]) => unknown;
    run: (params: unknown[]) => void;
  } {
    return {
      get: (params: unknown[]): unknown => {
        // SELECT model, dimension, slope, offset, sample_count, updated_at FROM model_calibrations WHERE model = ? AND dimension = ?
        if (sql.includes("SELECT model, dimension, slope, offset")) {
          const model = params[0] as string;
          const dimension = params[1] as string;
          const key = `${model}:${dimension}`;
          const row = this.rows.get(key);
          if (!row) {return undefined;}
          return {
            model: row.model,
            dimension: row.dimension,
            slope: row.slope,
            offset: row.offset,
            sampleCount: row.sample_count,
            updatedAt: row.updated_at,
          };
        }
        return undefined;
      },
      run: (params: unknown[]): void => {
        // INSERT OR REPLACE INTO model_calibrations (model, dimension, slope, offset, sample_count, updated_at) VALUES (?, ?, ?, ?, ?, ?)
        if (sql.includes("INSERT OR REPLACE INTO model_calibrations")) {
          const row: CalibrationRow = {
            model: params[0] as string,
            dimension: params[1] as string,
            slope: params[2] as number,
            offset: params[3] as number,
            sample_count: params[4] as number,
            updated_at: params[5] as string,
          };
          this.rows.set(`${row.model}:${row.dimension}`, row);
          return;
        }
      },
    };
  }

  /** Récupère toutes les calibrations stockées (pour vérifications) */
  getAllRows(): CalibrationRow[] {
    return Array.from(this.rows.values());
  }
}

// ── Tests CalibrationService (SDD §12.5) ──

describe("CalibrationService", () => {
  let db: MockCalibrationDatabase;
  let service: CalibrationService;

  beforeEach(() => {
    db = new MockCalibrationDatabase();
    service = new CalibrationService(db as never);
  });

  describe("calibrateScore", () => {
    it("devrait retourner le score brut borné [0, 100] sans calibration", () => {
      const result = service.calibrateScore(50, "test-model", "grammar");
      expect(result).toBe(50);
    });

    it("devrait appliquer la calibration slope * raw + offset", () => {
      const calibration: ModelCalibration = {
        model: "test-model",
        dimension: "grammar",
        slope: 1.2,
        offset: -10,
        sampleCount: 20,
        updatedAt: new Date().toISOString(),
      };
      service.storeCalibration(calibration);

      // raw=50 → 50 * 1.2 + (-10) = 50
      expect(service.calibrateScore(50, "test-model", "grammar")).toBe(50);
      // raw=80 → 80 * 1.2 + (-10) = 86
      expect(service.calibrateScore(80, "test-model", "grammar")).toBe(86);
    });

    it("devrait borner le score calibré à 100 maximum", () => {
      const calibration: ModelCalibration = {
        model: "test-model",
        dimension: "grammar",
        slope: 2,
        offset: 50,
        sampleCount: 10,
        updatedAt: new Date().toISOString(),
      };
      service.storeCalibration(calibration);

      // raw=80 → 80 * 2 + 50 = 210 → borné à 100
      expect(service.calibrateScore(80, "test-model", "grammar")).toBe(100);
    });

    it("devrait borner le score calibré à 0 minimum", () => {
      const calibration: ModelCalibration = {
        model: "test-model",
        dimension: "grammar",
        slope: 0.5,
        offset: -100,
        sampleCount: 10,
        updatedAt: new Date().toISOString(),
      };
      service.storeCalibration(calibration);

      // raw=50 → 50 * 0.5 + (-100) = -75 → borné à 0
      expect(service.calibrateScore(50, "test-model", "grammar")).toBe(0);
    });

    it("devrait arrondir le score calibré", () => {
      const calibration: ModelCalibration = {
        model: "test-model",
        dimension: "grammar",
        slope: 1.1,
        offset: 5,
        sampleCount: 10,
        updatedAt: new Date().toISOString(),
      };
      service.storeCalibration(calibration);

      // raw=50 → 50 * 1.1 + 5 = 60 → arrondi à 60
      expect(service.calibrateScore(50, "test-model", "grammar")).toBe(60);
      // raw=33 → 33 * 1.1 + 5 = 41.3 → arrondi à 41
      expect(service.calibrateScore(33, "test-model", "grammar")).toBe(41);
    });

    it("devrait gérer des modèles différents indépendamment", () => {
      const cal1: ModelCalibration = {
        model: "model-a",
        dimension: "grammar",
        slope: 1,
        offset: 0,
        sampleCount: 5,
        updatedAt: new Date().toISOString(),
      };
      const cal2: ModelCalibration = {
        model: "model-b",
        dimension: "grammar",
        slope: 0.8,
        offset: 20,
        sampleCount: 5,
        updatedAt: new Date().toISOString(),
      };
      service.storeCalibration(cal1);
      service.storeCalibration(cal2);

      // model-a : 50 * 1 + 0 = 50
      expect(service.calibrateScore(50, "model-a", "grammar")).toBe(50);
      // model-b : 50 * 0.8 + 20 = 60
      expect(service.calibrateScore(50, "model-b", "grammar")).toBe(60);
    });
  });

  describe("computeRegression", () => {
    it("devrait retourner slope=1, offset=0 pour moins de 2 échantillons", () => {
      const result = service.computeRegression([{ raw: 50, annotated: 50 }]);
      expect(result.slope).toBe(1);
      expect(result.offset).toBe(0);
      expect(result.sampleCount).toBe(1);
    });

    it("devrait calculer une régression linéaire simple (parfaite)", () => {
      // y = 2x + 10 : points (10, 30), (20, 50), (30, 70)
      const samples = [
        { raw: 10, annotated: 30 },
        { raw: 20, annotated: 50 },
        { raw: 30, annotated: 70 },
      ];
      const result = service.computeRegression(samples);
      expect(result.slope).toBeCloseTo(2, 5);
      expect(result.offset).toBeCloseTo(10, 5);
      expect(result.sampleCount).toBe(3);
    });

    it("devrait calculer une régression linéaire avec bruit", () => {
      // Approximativement y = x : points (10, 12), (20, 18), (30, 31), (40, 39)
      const samples = [
        { raw: 10, annotated: 12 },
        { raw: 20, annotated: 18 },
        { raw: 30, annotated: 31 },
        { raw: 40, annotated: 39 },
      ];
      const result = service.computeRegression(samples);
      // slope devrait être proche de 1, offset proche de 0
      expect(result.slope).toBeGreaterThan(0.8);
      expect(result.slope).toBeLessThan(1.2);
      expect(result.sampleCount).toBe(4);
    });

    it("devrait retourner slope=1, offset=0 si tous les scores bruts sont identiques", () => {
      const samples = [
        { raw: 50, annotated: 50 },
        { raw: 50, annotated: 60 },
        { raw: 50, annotated: 40 },
      ];
      const result = service.computeRegression(samples);
      expect(result.slope).toBe(1);
      expect(result.offset).toBe(0);
    });
  });

  describe("storeCalibration / loadCalibration", () => {
    it("devrait stocker et charger une calibration", () => {
      const calibration: ModelCalibration = {
        model: "qwen3.5:9b",
        dimension: "grammar",
        slope: 1.1,
        offset: -5,
        sampleCount: 20,
        updatedAt: "2025-01-01T00:00:00.000Z",
      };
      service.storeCalibration(calibration);

      const loaded = service.loadCalibration("qwen3.5:9b", "grammar");
      expect(loaded).toBeDefined();
      expect(loaded?.model).toBe("qwen3.5:9b");
      expect(loaded?.dimension).toBe("grammar");
      expect(loaded?.slope).toBe(1.1);
      expect(loaded?.offset).toBe(-5);
      expect(loaded?.sampleCount).toBe(20);
    });

    it("devrait retourner undefined pour une calibration inexistante", () => {
      const loaded = service.loadCalibration("unknown-model", "unknown-dim");
      expect(loaded).toBeUndefined();
    });

    it("devrait mettre à jour une calibration existante (UPSERT)", () => {
      const cal1: ModelCalibration = {
        model: "qwen3.5:9b",
        dimension: "grammar",
        slope: 1,
        offset: 0,
        sampleCount: 10,
        updatedAt: "2025-01-01T00:00:00.000Z",
      };
      service.storeCalibration(cal1);

      const cal2: ModelCalibration = {
        model: "qwen3.5:9b",
        dimension: "grammar",
        slope: 1.2,
        offset: -5,
        sampleCount: 20,
        updatedAt: "2025-02-01T00:00:00.000Z",
      };
      service.storeCalibration(cal2);

      const loaded = service.loadCalibration("qwen3.5:9b", "grammar");
      expect(loaded?.slope).toBe(1.2);
      expect(loaded?.offset).toBe(-5);
      expect(loaded?.sampleCount).toBe(20);
    });
  });

  describe("calibrateFromReference", () => {
    it("devrait calibrer plusieurs dimensions à partir d'un jeu de référence", () => {
      const referenceData = {
        grammar: [
          { raw: 50, annotated: 60 },
          { raw: 70, annotated: 80 },
          { raw: 90, annotated: 100 },
        ],
        style: [
          { raw: 40, annotated: 50 },
          { raw: 60, annotated: 70 },
        ],
      };

      service.calibrateFromReference("test-model", referenceData);

      const grammarCal = service.loadCalibration("test-model", "grammar");
      expect(grammarCal).toBeDefined();
      expect(grammarCal?.sampleCount).toBe(3);

      const styleCal = service.loadCalibration("test-model", "style");
      expect(styleCal).toBeDefined();
      expect(styleCal?.sampleCount).toBe(2);
    });
  });

  describe("shouldRecalibrate", () => {
    it("devrait retourner true si aucune calibration n'existe", () => {
      expect(service.shouldRecalibrate("new-model", 0)).toBe(true);
    });

    it("devrait retourner true tous les 100 chapitres", () => {
      // Stocker une calibration pour que le modèle soit calibré
      service.storeCalibration({
        model: "test-model",
        dimension: "grammar",
        slope: 1,
        offset: 0,
        sampleCount: 10,
        updatedAt: new Date().toISOString(),
      });

      expect(service.shouldRecalibrate("test-model", 50)).toBe(false);
      expect(service.shouldRecalibrate("test-model", 100)).toBe(true);
      expect(service.shouldRecalibrate("test-model", 150)).toBe(false);
      expect(service.shouldRecalibrate("test-model", 200)).toBe(true);
    });
  });
});

// ── Tests HallucinationDetector (SDD §12.6) ──

describe("HallucinationDetector", () => {
  let detector: HallucinationDetector;

  beforeEach(() => {
    detector = new HallucinationDetector();
  });

  describe("detect", () => {
    it("devrait retourner un score de 100 sans hallucinations", () => {
      const source = "Alice went to the park.";
      const target = "Alice est allée au parc.";
      const report = detector.detect(source, target, "en", "fr");

      expect(report.score).toBe(100);
      expect(report.inventedEntities.length).toBe(0);
      expect(report.suspiciousReferences.length).toBe(0);
    });

    it("devrait détecter un nom propre inventé dans la cible", () => {
      const source = "Alice went to the park.";
      const target = "Alice est allée au parc avec Bob.";
      const report = detector.detect(source, target, "en", "fr");

      // "Bob" est un nom propre présent dans la cible mais absent du source
      expect(report.inventedEntities.length).toBeGreaterThan(0);
      expect(report.inventedEntities).toContain("bob");
      expect(report.score).toBeLessThan(100);
    });

    it("devrait détecter plusieurs entités inventées", () => {
      const source = "The cat sat on the mat.";
      const target = "Alice and Bob went to Paris with Charlie.";
      const report = detector.detect(source, target, "en", "fr");

      expect(report.inventedEntities.length).toBeGreaterThanOrEqual(3);
      expect(report.inventedEntities).toContain("alice");
      expect(report.inventedEntities).toContain("bob");
      expect(report.inventedEntities).toContain("charlie");
      expect(report.score).toBeLessThan(100);
    });

    it("devrait ne pas signaler les entités présentes dans le source", () => {
      const source = "Alice and Bob went to Paris.";
      const target = "Alice et Bob sont allés à Paris.";
      const report = detector.detect(source, target, "en", "fr");

      // Alice, Bob, Paris sont dans le source ET la cible
      expect(report.inventedEntities).not.toContain("alice");
      expect(report.inventedEntities).not.toContain("bob");
      expect(report.inventedEntities).not.toContain("paris");
    });

    it("devrait détecter une référence à un chapitre suspecte", () => {
      const source = "The hero entered the cave.";
      const target = "Le héros entra dans la grotte. Voir chapitre 42.";
      const report = detector.detect(source, target, "en", "fr");

      expect(report.suspiciousReferences.length).toBeGreaterThan(0);
      expect(report.score).toBeLessThan(100);
    });

    it("devrait générer des avertissements détaillés", () => {
      const source = "The cat sat.";
      const target = "Alice went to Paris. Chapter 99.";
      const report = detector.detect(source, target, "en", "fr");

      expect(report.warnings.length).toBeGreaterThan(0);
      // Au moins un avertissement mentionne une entité inventée
      const hasEntityWarning = report.warnings.some((w) =>
        w.includes("Entité nommée potentiellement inventée"),
      );
      expect(hasEntityWarning).toBe(true);
    });

    it("devrait gérer un texte source vide", () => {
      const report = detector.detect("", "Alice went to Paris.", "en", "fr");
      expect(report.score).toBeLessThanOrEqual(100);
      expect(report.inventedEntities.length).toBeGreaterThan(0);
    });

    it("devrait gérer un texte cible vide", () => {
      const report = detector.detect("Alice went to Paris.", "", "en", "fr");
      expect(report.score).toBe(100);
      expect(report.inventedEntities.length).toBe(0);
    });
  });

  describe("extractNamedEntities", () => {
    it("devrait extraire les noms propres d'un texte latin", () => {
      const entities = detector.extractNamedEntities(
        "Alice and Bob went to Paris.",
        "en",
      );
      expect(entities.has("alice")).toBe(true);
      expect(entities.has("bob")).toBe(true);
      expect(entities.has("paris")).toBe(true);
    });

    it("devrait extraire les caractères CJK d'un texte chinois", () => {
      const entities = detector.extractNamedEntities("张三去了北京。", "zh");
      // Les séquences CJK de 2+ caractères sont extraites
      expect(entities.size).toBeGreaterThan(0);
    });

    it("devrait filtrer les mots communs", () => {
      const entities = detector.extractNamedEntities("The cat is here.", "en");
      // "The" est un mot commun, ne doit pas être dans les entités
      expect(entities.has("the")).toBe(false);
    });
  });
});

// ── Tests ConsistencyChecker avec tolérances (SDD §11.4) ──

describe("ConsistencyChecker — tolérances configurables", () => {
  let checker: ConsistencyChecker;

  beforeEach(() => {
    checker = new ConsistencyChecker();
  });

  describe("tolérances par défaut", () => {
    it("devrait avoir des tolérances par défaut pour les paires courantes", () => {
      expect(DEFAULT_TOLERANCES["zh-fr"]).toBeDefined();
      expect(DEFAULT_TOLERANCES["ja-fr"]).toBeDefined();
      expect(DEFAULT_TOLERANCES["ko-fr"]).toBeDefined();
      expect(DEFAULT_TOLERANCES["en-fr"]).toBeDefined();
      expect(DEFAULT_TOLERANCES["zh-en"]).toBeDefined();
      expect(DEFAULT_TOLERANCES["ja-en"]).toBeDefined();
    });

    it("devrait avoir des tolérances plus larges pour zh-fr que pour en-fr", () => {
      const zhFr = DEFAULT_TOLERANCES["zh-fr"];
      const enFr = DEFAULT_TOLERANCES["en-fr"];
      // Le chinois → français a des ratios plus larges (le français est plus long)
      expect(zhFr.lengthRatioMax).toBeGreaterThan(enFr.lengthRatioMax);
    });

    it("devrait retourner la tolérance par défaut pour une paire inconnue", () => {
      const tol = checker.getTolerance("xx-yy");
      expect(tol).toEqual(DEFAULT_TOLERANCE);
    });
  });

  describe("setTolerance", () => {
    it("devrait permettre de définir une tolérance personnalisée", () => {
      const custom = {
        sentenceRatioMin: 0.3,
        sentenceRatioMax: 3.0,
        lengthRatioMin: 0.4,
        lengthRatioMax: 4.0,
        ignoreNumbersInDialogues: true,
        ignorePunctuationMismatch: true,
      };
      checker.setTolerance("zh-fr", custom);

      const tol = checker.getTolerance("zh-fr");
      expect(tol.sentenceRatioMin).toBe(0.3);
      expect(tol.sentenceRatioMax).toBe(3.0);
      expect(tol.ignoreNumbersInDialogues).toBe(true);
    });

    it("devrait permettre de définir toutes les tolérances d'un coup", () => {
      const custom = {
        "en-fr": {
          sentenceRatioMin: 0.9,
          sentenceRatioMax: 1.1,
          lengthRatioMin: 0.8,
          lengthRatioMax: 1.2,
          ignoreNumbersInDialogues: false,
          ignorePunctuationMismatch: false,
        },
      };
      checker.setTolerances(custom);

      const tol = checker.getTolerance("en-fr");
      expect(tol.sentenceRatioMin).toBe(0.9);
      expect(tol.sentenceRatioMax).toBe(1.1);
    });
  });

  describe("check avec tolérances", () => {
    it("devrait accepter un ratio de longueur dans la tolérance zh-fr", () => {
      // Source chinois (long), cible française (environ 2x plus long) — ratio ~2.0
      const source = [
        "这是一个关于英雄的很长很长的故事，他去了远方寻找宝藏。在这个过程中他遇到了很多困难和挑战，但是他从来没有放弃过。最终他找到了宝藏并且回到了家乡。他的故事被人们传颂了很久很久，成为了传说中的传奇。",
      ];
      const target = [
        "Ceci est une longue histoire sur un héros qui est parti chercher un trésor. Il a rencontré beaucoup de difficultés mais n'a jamais abandonné. Finalement il a trouvé le trésor et est rentré chez lui.",
      ];
      const report = checker.check(source, target, [], "zh-fr");

      // Le ratio de longueur devrait être dans la tolérance zh-fr (max 2.5)
      const lengthMetric = report.metrics.find((m) => m.name === "length");
      expect(lengthMetric).toBeDefined();
      expect(lengthMetric?.ok).toBe(true);
    });

    it("devrait signaler un ratio de longueur hors tolérance en-fr", () => {
      // Source courte (anglais), cible très longue (français) — ratio > 1.4
      const source = ["Hi."];
      const target = [
        "Bonjour, ceci est une phrase très longue qui dépasse largement la tolérance attendue pour la paire anglais-français.",
      ];
      const report = checker.check(source, target, [], "en-fr");

      // Le ratio de longueur devrait dépasser la tolérance en-fr (max 1.4)
      const lengthMetric = report.metrics.find((m) => m.name === "length");
      expect(lengthMetric).toBeDefined();
      expect(lengthMetric?.ok).toBe(false);

      // Un avertissement devrait mentionner le ratio hors tolérance
      const lengthWarning = report.warnings.find((w) =>
        w.message.includes("Ratio de longueur hors tolerance"),
      );
      expect(lengthWarning).toBeDefined();
    });

    it("devrait ignorer la ponctuation si ignorePunctuationMismatch est true", () => {
      const source = ["Hello, world! How are you?"];
      const target = ["Bonjour le monde。 Comment allez-vous ？"];

      // Avec zh-fr (ignorePunctuationMismatch = true), la ponctuation est ignorée
      const report = checker.check(source, target, [], "zh-fr");
      const lengthMetric = report.metrics.find((m) => m.name === "length");
      expect(lengthMetric).toBeDefined();
      // Le ratio devrait être calculé sans ponctuation
      expect(lengthMetric?.ok).toBe(true);
    });

    it("devrait compter les phrases avec les métriques", () => {
      const source = ["First sentence. Second sentence! Third?"];
      const target = ["Première phrase. Deuxième phrase ! Troisième ?"];
      const report = checker.check(source, target, [], "en-fr");

      const sentenceMetric = report.metrics.find((m) => m.name === "sentences");
      expect(sentenceMetric).toBeDefined();
      expect(sentenceMetric?.source).toBe(3);
      expect(sentenceMetric?.target).toBe(3);
      expect(sentenceMetric?.ok).toBe(true);
    });

    it("devrait signaler un ratio de phrases hors tolérance", () => {
      const source = ["One sentence."];
      const target = [
        "Première phrase. Deuxième phrase. Troisième phrase. Quatrième.",
      ];
      const report = checker.check(source, target, [], "en-fr");

      const sentenceMetric = report.metrics.find((m) => m.name === "sentences");
      expect(sentenceMetric).toBeDefined();
      expect(sentenceMetric?.ok).toBe(false);

      const sentenceWarning = report.warnings.find((w) =>
        w.message.includes("Ratio de phrases hors tolerance"),
      );
      expect(sentenceWarning).toBeDefined();
    });
  });

  describe("rétrocompatibilité", () => {
    it("devrait fonctionner sans paire de langues (comportement existant)", () => {
      const report = checker.check(["a", "b"], ["a"], []);
      expect(report.warnings.length).toBeGreaterThan(0);
      expect(report.globalScore).toBeLessThan(100);
    });
  });
});

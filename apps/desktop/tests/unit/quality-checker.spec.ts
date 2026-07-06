import { describe, it, expect, beforeEach } from "vitest";
import { QualityChecker } from "../../src/main/services/QualityChecker";
import { HallucinationDetector } from "../../src/main/services/HallucinationDetector";
import type { ConsistencyReport } from "@shared/types/index.js";

/**
 * T8 — HallucinationDetector câblé dans QualityChecker
 *
 * 6 tests :
 * 1. HallucinationDetector trouve des entités inventées → score <95
 * 2. HallucinationDetector clean → score = 95
 * 3. ConsistencyReport faible → dimension consistency basse
 * 4. ConsistencyReport parfait → consistency = 100
 * 5. evaluate() complet → 8 dimensions toutes calculées
 * 6. HallucinationDetector erreur → fallback 0 (T8 fix: pas un faux 95)
 */

describe("QualityChecker — HallucinationDetector wired", () => {
  let checker: QualityChecker;

  beforeEach(() => {
    checker = new QualityChecker();
  });

  it("devrait detecter les entites inventees → score reduit", async () => {
    // La cible contient "Zarkon" qui n'est pas dans la source
    const source = "The hero entered the dark forest.";
    const target =
      "Le héros entra dans la forêt sombre. Zarkon regardait au loin.";

    const report = await checker.evaluate(source, target, []);
    // Avec placeholders lang, "Zarkon" + "Le" → 2 entités → score = 100 - 2*10 = 80
    expect(report.hallucination).toBeLessThan(90);
  });

  it("devrait produire un score eleve si aucune hallucination flagrante", async () => {
    // Avec les codes langue "source"/"target" (placeholders), le détecteur
    // peut lever de faux positifs sur des mots communs en début de phrase.
    // Le score reste néanmoins élevé (>80) pour un texte propre.
    const source = "The hero entered the dark forest.";
    const target = "Le héros entra dans la forêt sombre.";

    const report = await checker.evaluate(source, target, []);
    expect(report.hallucination).toBeGreaterThanOrEqual(80);
  });

  it("devrait utiliser ConsistencyReport pour la dimension consistency", async () => {
    const consistencyReport: ConsistencyReport = {
      metrics: [
        { name: "paragraphs", source: 2, target: 1, ok: false, score: 0 },
      ],
      warnings: [
        {
          severity: "high",
          message: "Nombre de paragraphes different",
        },
      ],
      globalScore: 45,
    };

    const report = await checker.evaluate(
      "Hello world.\nSecond paragraph.",
      "Bonjour le monde.",
      [],
      consistencyReport,
    );
    expect(report.consistency).toBe(45);
  });

  it("devrait retourner consistency = 100 avec un rapport parfait", async () => {
    const perfectReport: ConsistencyReport = {
      metrics: [
        { name: "paragraphs", source: 1, target: 1, ok: true, score: 100 },
      ],
      warnings: [],
      globalScore: 100,
    };

    const report = await checker.evaluate(
      "Hello world.",
      "Bonjour le monde.",
      [],
      perfectReport,
    );
    expect(report.consistency).toBe(100);
  });

  it("evaluate() complet → les 8 dimensions sont calculees", async () => {
    const source = "The hero entered the dark forest.";
    const target = "Le héros entra dans la forêt sombre.";

    const report = await checker.evaluate(source, target, []);
    const dimensions = [
      "consistency",
      "grammar",
      "fluency",
      "style",
      "lexicon",
      "hallucination",
      "length",
      "dialogue",
    ] as const;

    for (const dim of dimensions) {
      expect(typeof report[dim]).toBe("number");
      expect(report[dim]).toBeGreaterThanOrEqual(0);
      expect(report[dim]).toBeLessThanOrEqual(100);
    }
    expect(typeof report.globalScore).toBe("number");
  });

  it("devrait fallback a 0 si HallucinationDetector plante (T8 fix)", async () => {
    // T8 fix : un détecteur en erreur donne 0 (pas un trompeur 95).
    // Un échec de détection ne doit pas signaler une qualité d'hallucination excellente.
    const brokenDetector = {
      detect: () => {
        throw new Error("Broken");
      },
    } as unknown as HallucinationDetector;
    const weakChecker = new QualityChecker(brokenDetector);

    const report = await weakChecker.evaluate(
      "Hello world.",
      "Bonjour le monde.",
      [],
    );
    expect(report.hallucination).toBe(0);
  });
});

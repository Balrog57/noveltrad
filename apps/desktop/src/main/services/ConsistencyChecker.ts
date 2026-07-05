import type {
  ConsistencyReport,
  ConsistencyTolerance,
  LexiconEntry,
} from "@shared/types/index.js";
import tokenizer from "sbd";

/**
 * SDD §11.4 : Tolérances par défaut pour les paires de langues courantes.
 *
 * Les langues asiatiques (zh, ja, ko) vers le français ont des ratios de
 * longueur très différents (le chinois est plus compact que le français).
 * Les paires latines (en-fr) ont des ratios plus proches de 1.
 */
export const DEFAULT_TOLERANCES: Record<string, ConsistencyTolerance> = {
  // Paires asiatiques → français (le français est généralement plus long)
  "zh-fr": {
    sentenceRatioMin: 0.5,
    sentenceRatioMax: 2.0,
    lengthRatioMin: 0.6,
    lengthRatioMax: 2.5,
    ignoreNumbersInDialogues: true,
    ignorePunctuationMismatch: true,
  },
  "ja-fr": {
    sentenceRatioMin: 0.5,
    sentenceRatioMax: 2.0,
    lengthRatioMin: 0.6,
    lengthRatioMax: 2.5,
    ignoreNumbersInDialogues: true,
    ignorePunctuationMismatch: true,
  },
  "ko-fr": {
    sentenceRatioMin: 0.5,
    sentenceRatioMax: 2.0,
    lengthRatioMin: 0.6,
    lengthRatioMax: 2.5,
    ignoreNumbersInDialogues: true,
    ignorePunctuationMismatch: true,
  },
  // Paires latines → français (ratios proches de 1)
  "en-fr": {
    sentenceRatioMin: 0.8,
    sentenceRatioMax: 1.3,
    lengthRatioMin: 0.7,
    lengthRatioMax: 1.4,
    ignoreNumbersInDialogues: false,
    ignorePunctuationMismatch: false,
  },
  // Paires asiatiques → anglais
  "zh-en": {
    sentenceRatioMin: 0.6,
    sentenceRatioMax: 1.8,
    lengthRatioMin: 0.5,
    lengthRatioMax: 2.2,
    ignoreNumbersInDialogues: true,
    ignorePunctuationMismatch: true,
  },
  "ja-en": {
    sentenceRatioMin: 0.6,
    sentenceRatioMax: 1.8,
    lengthRatioMin: 0.5,
    lengthRatioMax: 2.2,
    ignoreNumbersInDialogues: true,
    ignorePunctuationMismatch: true,
  },
};

/** Tolérance par défaut (utilisée si la paire de langues n'est pas configurée) */
export const DEFAULT_TOLERANCE: ConsistencyTolerance = {
  sentenceRatioMin: 0.7,
  sentenceRatioMax: 1.5,
  lengthRatioMin: 0.6,
  lengthRatioMax: 1.8,
  ignoreNumbersInDialogues: false,
  ignorePunctuationMismatch: false,
};

export class ConsistencyChecker {
  /** Tolérances configurables par paire de langues (SDD §11.4) */
  private tolerances: Record<string, ConsistencyTolerance> = {
    ...DEFAULT_TOLERANCES,
  };

  /**
   * Définit les tolérances pour une paire de langues.
   * @param pair Paire au format "source-cible" (ex: "zh-fr")
   * @param tolerance Tolérances à appliquer
   */
  setTolerance(pair: string, tolerance: ConsistencyTolerance): void {
    this.tolerances[pair] = tolerance;
  }

  /**
   * Définit toutes les tolérances d'un coup (remplace les existantes).
   */
  setTolerances(tolerances: Record<string, ConsistencyTolerance>): void {
    this.tolerances = { ...DEFAULT_TOLERANCES, ...tolerances };
  }

  /**
   * Récupère les tolérances pour une paire de langues.
   * Retourne la tolérance par défaut si la paire n'est pas configurée.
   */
  getTolerance(pair: string): ConsistencyTolerance {
    return this.tolerances[pair] ?? DEFAULT_TOLERANCE;
  }

  /**
   * Vérifie la cohérence entre le source et la cible.
   *
   * @param source Paragraphes source
   * @param target Paragraphes cible (traduction)
   * @param lexicon Entrées lexicales (termes verrouillés vérifiés)
   * @param languagePair Paire de langues optionnelle (ex: "zh-fr") pour appliquer les tolérances
   */
  check(
    source: string[],
    target: string[],
    lexicon: LexiconEntry[],
    languagePair?: string,
  ): ConsistencyReport {
    const tolerance = languagePair
      ? this.getTolerance(languagePair)
      : DEFAULT_TOLERANCE;

    const metrics = [
      {
        name: "paragraphs",
        source: source.length,
        target: target.length,
        ok: source.length === target.length,
      },
    ];

    const warnings: ConsistencyReport["warnings"] = [];
    if (source.length !== target.length) {
      warnings.push({
        severity: "high",
        message: `Nombre de paragraphes different : ${source.length} source, ${target.length} cible`,
      });
    }

    // SDD §11.4 : vérification du ratio de phrases avec tolérances configurables
    const sourceSentences = this.countSentences(source.join(" "));
    const targetSentences = this.countSentences(target.join(" "));
    if (sourceSentences > 0) {
      const sentenceRatio = targetSentences / sourceSentences;
      metrics.push({
        name: "sentences",
        source: sourceSentences,
        target: targetSentences,
        ok:
          sentenceRatio >= tolerance.sentenceRatioMin &&
          sentenceRatio <= tolerance.sentenceRatioMax,
      });
      if (
        sentenceRatio < tolerance.sentenceRatioMin ||
        sentenceRatio > tolerance.sentenceRatioMax
      ) {
        warnings.push({
          severity: "medium",
          message: `Ratio de phrases hors tolerance : ${sentenceRatio.toFixed(2)} (attendu ${tolerance.sentenceRatioMin}-${tolerance.sentenceRatioMax})`,
        });
      }
    }

    // SDD §11.4 : vérification du ratio de longueur avec tolérances configurables
    const sourceLen = this.computeLength(source.join(" "), tolerance);
    const targetLen = this.computeLength(target.join(" "), tolerance);
    if (sourceLen > 0) {
      const lengthRatio = targetLen / sourceLen;
      metrics.push({
        name: "length",
        source: sourceLen,
        target: targetLen,
        ok:
          lengthRatio >= tolerance.lengthRatioMin &&
          lengthRatio <= tolerance.lengthRatioMax,
      });
      if (
        lengthRatio < tolerance.lengthRatioMin ||
        lengthRatio > tolerance.lengthRatioMax
      ) {
        warnings.push({
          severity: "medium",
          message: `Ratio de longueur hors tolerance : ${lengthRatio.toFixed(2)} (attendu ${tolerance.lengthRatioMin}-${tolerance.lengthRatioMax})`,
        });
      }
    }

    // Vérification des termes verrouillés du lexique
    for (const entry of lexicon.filter((e) => e.locked)) {
      const pattern = new RegExp(
        `\\b${this.escapeRegExp(entry.term)}\\b`,
        "gi",
      );
      const sourceMatches = source.join(" ").match(pattern) ?? [];
      const targetMatches = target.join(" ").match(pattern) ?? [];
      if (sourceMatches.length > 0 && targetMatches.length === 0) {
        warnings.push({
          severity: "high",
          message: `Terme verrouille "${entry.term}" absent de la cible`,
        });
      }
    }

    const globalScore =
      warnings.length === 0 ? 100 : Math.max(0, 100 - warnings.length * 15);

    return { metrics, warnings, globalScore };
  }

  /**
   * Compte le nombre de phrases dans un texte.
   * Utilise `sbd` (Sentence Boundary Detection) pour une détection
   * plus précise que le simple split sur la ponctuation.
   * Pour les textes CJK non gérés par sbd, un split supplémentaire
   * sur la ponctuation CJK (。！？) est appliqué.
   */
  private countSentences(text: string): number {
    if (!text.trim()) {return 0;}
    const sbdSentences = tokenizer.sentences(text, {});
    const sentences = sbdSentences.flatMap((s: string) =>
      s.split(/[。！？]+/).filter((p: string) => p.trim().length > 0),
    );
    return sentences.length;
  }

  /**
   * Calcule la longueur d'un texte en appliquant les tolérances.
   *
   * Si `ignoreNumbersInDialogues` est true, les nombres entre guillemets
   * sont ignorés (les dialogues peuvent contenir des nombres qui ne
   * doivent pas affecter le ratio de longueur).
   *
   * Si `ignorePunctuationMismatch` est true, la ponctuation est retirée
   * du calcul de longueur (les langues asiatiques utilisent une ponctuation
   * différente).
   */
  private computeLength(text: string, tolerance: ConsistencyTolerance): number {
    let processed = text;

    if (tolerance.ignoreNumbersInDialogues) {
      // Retirer les nombres entre guillemets (« " » ou 「」)
      processed = processed.replace(/[「「"][^」」"]*\d+[^」」"]*["」」]/g, "");
    }

    if (tolerance.ignorePunctuationMismatch) {
      // Retirer la ponctuation (latine et CJK)
      processed = processed.replace(
        /[.,;:!?。、；：！？""''「」『』（）()]/g,
        "",
      );
    }

    return processed.length;
  }

  private escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }
}

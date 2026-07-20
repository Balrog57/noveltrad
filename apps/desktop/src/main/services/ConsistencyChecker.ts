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
  // Paires asiatiques → français (SDD §11.3: ratios de phrases resserrés)
  "zh-fr": {
    sentenceRatioMin: 0.95,
    sentenceRatioMax: 1.05,
    lengthRatioMin: 0.5,
    lengthRatioMax: 1.5,
    ignoreNumbersInDialogues: true,
    ignorePunctuationMismatch: true,
  },
  "ja-fr": {
    sentenceRatioMin: 0.95,
    sentenceRatioMax: 1.05,
    lengthRatioMin: 0.5,
    lengthRatioMax: 1.5,
    ignoreNumbersInDialogues: true,
    ignorePunctuationMismatch: true,
  },
  "ko-fr": {
    sentenceRatioMin: 0.95,
    sentenceRatioMax: 1.05,
    lengthRatioMin: 0.5,
    lengthRatioMax: 1.5,
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
    sentenceRatioMin: 0.8,
    sentenceRatioMax: 1.2,
    lengthRatioMin: 0.5,
    lengthRatioMax: 1.8,
    ignoreNumbersInDialogues: true,
    ignorePunctuationMismatch: true,
  },
  "ja-en": {
    sentenceRatioMin: 0.8,
    sentenceRatioMax: 1.2,
    lengthRatioMin: 0.5,
    lengthRatioMax: 1.8,
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

/**
 * Poids SDD §11.5 pour le calcul du score pondéré.
 */
const METRIC_WEIGHTS: Record<string, number> = {
  paragraphs: 30,
  sentences: 15,
  dialogues: 15,
  length: 10,
  namedEntities: 15,
  numbers: 10,
  markup: 5,
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

    const metrics: ConsistencyReport["metrics"] = [];
    const warnings: ConsistencyReport["warnings"] = [];

    // ── 1. Paragraphs ──
    const paragraphOk = source.length === target.length;
    metrics.push({
      name: "paragraphs",
      source: source.length,
      target: target.length,
      ok: paragraphOk,
      score: paragraphOk ? 100 : 0,
    });
    if (!paragraphOk) {
      warnings.push({
        severity: "high",
        message: `Nombre de paragraphes different : ${source.length} source, ${target.length} cible`,
      });
    }

    // ── 2. Sentences (SDD §11.4) ──
    const sourceSentences = this.countSentences(source.join(" "));
    const targetSentences = this.countSentences(target.join(" "));
    let sentenceOk = true;
    if (sourceSentences > 0) {
      const sentenceRatio = targetSentences / sourceSentences;
      sentenceOk =
        sentenceRatio >= tolerance.sentenceRatioMin &&
        sentenceRatio <= tolerance.sentenceRatioMax;
      metrics.push({
        name: "sentences",
        source: sourceSentences,
        target: targetSentences,
        ok: sentenceOk,
        score: sentenceOk ? 100 : Math.max(0, 100 - Math.abs(1 - sentenceRatio) * 100),
      });
      if (!sentenceOk) {
        warnings.push({
          severity: "medium",
          message: `Ratio de phrases hors tolerance : ${sentenceRatio.toFixed(2)} (attendu ${tolerance.sentenceRatioMin}-${tolerance.sentenceRatioMax})`,
        });
      }
    } else {
      metrics.push({
        name: "sentences",
        source: 0,
        target: 0,
        ok: true,
        score: 100,
      });
    }

    // ── 3. Length ratio (SDD §11.4) ──
    const sourceLen = this.computeLength(source.join(" "), tolerance);
    const targetLen = this.computeLength(target.join(" "), tolerance);
    let lengthOk = true;
    if (sourceLen > 0) {
      const lengthRatio = targetLen / sourceLen;
      lengthOk =
        lengthRatio >= tolerance.lengthRatioMin &&
        lengthRatio <= tolerance.lengthRatioMax;
      metrics.push({
        name: "length",
        source: sourceLen,
        target: targetLen,
        ok: lengthOk,
        score: lengthOk ? 100 : Math.max(0, 100 - Math.abs(1 - lengthRatio) * 100),
      });
      if (!lengthOk) {
        warnings.push({
          severity: "medium",
          message: `Ratio de longueur hors tolerance : ${lengthRatio.toFixed(2)} (attendu ${tolerance.lengthRatioMin}-${tolerance.lengthRatioMax})`,
        });
      }
    } else {
      metrics.push({
        name: "length",
        source: 0,
        target: 0,
        ok: true,
        score: 100,
      });
    }

    // ── 4. Dialogues (SDD §11.4) ──
    const dialogueWarnings = this.compareDialogues(source, target);
    warnings.push(...dialogueWarnings);
    const sourceDialogueCount = this.countDialogueMarkers(source.join(" "));
    const targetDialogueCount = this.countDialogueMarkers(target.join(" "));
    metrics.push({
      name: "dialogues",
      source: sourceDialogueCount,
      target: targetDialogueCount,
      ok: dialogueWarnings.length === 0,
      score:
        dialogueWarnings.length === 0
          ? 100
          : Math.max(0, 100 - dialogueWarnings.length * 25),
    });

    // ── 5. Named entities / locked terms ──
    let hasLockedNameMissing = false;
    const lockedEntries = lexicon.filter((e) => e.locked);
    for (const entry of lockedEntries) {
      const pattern = new RegExp(
        `\\b${this.escapeRegExp(entry.term)}\\b`,
        "gi",
      );
      const sourceMatches = source.join(" ").match(pattern) ?? [];
      const targetMatches = target.join(" ").match(pattern) ?? [];
      if (sourceMatches.length > 0 && targetMatches.length === 0) {
        hasLockedNameMissing = true;
        warnings.push({
          severity: "high",
          message: `Terme verrouille "${entry.term}" absent de la cible`,
        });
      }
    }
    metrics.push({
      name: "namedEntities",
      source: lockedEntries.length,
      target: lockedEntries.length,
      ok: !hasLockedNameMissing,
      score: hasLockedNameMissing ? 0 : 100,
    });

    // ── 6. Numbers (SDD §11.4) ──
    const numberWarnings = this.compareNumbers(source, target);
    warnings.push(...numberWarnings);
    const sourceNumbers = (source.join(" ").match(/\d+/g) || []).length;
    const targetNumbers = (target.join(" ").match(/\d+/g) || []).length;
    const hasMissingNumber = numberWarnings.some((w) =>
      w.message.includes("absent de la cible"),
    );
    metrics.push({
      name: "numbers",
      source: sourceNumbers,
      target: targetNumbers,
      ok: numberWarnings.length === 0,
      score:
        numberWarnings.length === 0
          ? 100
          : Math.max(0, 100 - numberWarnings.length * 15),
    });

    // ── 7. Markup (SDD §11.4) ──
    const markupWarnings = this.compareMarkup(source, target);
    warnings.push(...markupWarnings);
    metrics.push({
      name: "markup",
      source: this.countMarkupElements(source.join(" ")),
      target: this.countMarkupElements(target.join(" ")),
      ok: markupWarnings.length === 0,
      score: markupWarnings.length === 0 ? 100 : 0,
    });

    // ── Weighted score (SDD §11.5) ──
    let totalWeight = 0;
    let weightedSum = 0;
    for (const metric of metrics) {
      const weight = METRIC_WEIGHTS[metric.name] ?? 5;
      totalWeight += weight;
      weightedSum += metric.score * weight;
    }
    let globalScore = totalWeight > 0 ? Math.round(weightedSum / totalWeight) : 100;

    // ── Caps (SDD §11.5) ──
    if (!paragraphOk) {
      globalScore = Math.min(globalScore, 50);
    }
    if (hasLockedNameMissing) {
      globalScore = Math.min(globalScore, 70);
    }
    if (hasMissingNumber) {
      globalScore = Math.min(globalScore, 80);
    }

    return { metrics, warnings, globalScore };
  }

  // ── Private helpers ──

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
   */
  private computeLength(text: string, tolerance: ConsistencyTolerance): number {
    let processed = text;

    if (tolerance.ignoreNumbersInDialogues) {
      processed = processed.replace(/[「"][^」"]*\d+[^」"]*["」]/g, "");
    }

    if (tolerance.ignorePunctuationMismatch) {
      processed = processed.replace(
        /[.,;:!?，、。；：！？""''「」『』《》（）()]/g,
        "",
      );
    }

    return processed.length;
  }

  private escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  /**
   * SDD §11.4 : Compare les segments de dialogue entre source et cible.
   * Regex : 「」""'' + "— + - + «»
   * Avertit si l'écart > 20 %.
   */
  private compareDialogues(
    source: string[],
    target: string[],
  ): ConsistencyReport["warnings"] {
    const sourceCount = this.countDialogueMarkers(source.join(" "));
    const targetCount = this.countDialogueMarkers(target.join(" "));

    const warnings: ConsistencyReport["warnings"] = [];
    const max = Math.max(sourceCount, targetCount);
    if (max > 0) {
      const diff = Math.abs(sourceCount - targetCount) / max;
      if (diff > 0.2) {
        warnings.push({
          severity: "medium",
          message: `Nombre de segments de dialogue different : ${sourceCount} source, ${targetCount} cible (ecart ${(diff * 100).toFixed(0)}%)`,
        });
      }
    }
    return warnings;
  }

  /**
   * Compte les marqueurs de dialogue dans un texte.
   */
  private countDialogueMarkers(text: string): number {
    // SDD §11.4 : 「」 "" '' "— - «»
    const markers = /[「」""''—«»]/g;
    const matches = text.match(markers);
    return matches ? Math.ceil(matches.length / 2) : 0;
  }

  /**
   * SDD §11.4 : Compare les nombres entre source et cible.
   * Chaque nombre du source doit apparaître dans la cible.
   */
  private compareNumbers(
    source: string[],
    target: string[],
  ): ConsistencyReport["warnings"] {
    const sourceText = source.join(" ");
    const targetText = target.join(" ");

    const sourceNumbers = (sourceText.match(/\d+/g) || []).map(Number);
    const targetNumbers = (targetText.match(/\d+/g) || []).map(Number);

    const sourceFreq = new Map<number, number>();
    for (const n of sourceNumbers) {
      sourceFreq.set(n, (sourceFreq.get(n) || 0) + 1);
    }
    const targetFreq = new Map<number, number>();
    for (const n of targetNumbers) {
      targetFreq.set(n, (targetFreq.get(n) || 0) + 1);
    }

    const warnings: ConsistencyReport["warnings"] = [];

    for (const [num, count] of sourceFreq) {
      const targetCount = targetFreq.get(num) || 0;
      if (targetCount === 0) {
        warnings.push({
          severity: "medium",
          message: `Nombre "${num}" present dans le source mais absent de la cible`,
        });
      } else if (targetCount !== count) {
        warnings.push({
          severity: "low",
          message: `Nombre "${num}" : ${count} occurrence(s) source, ${targetCount} cible`,
        });
      }
    }

    for (const [num, count] of targetFreq) {
      const sourceCount = sourceFreq.get(num) || 0;
      if (sourceCount === 0) {
        warnings.push({
          severity: "low",
          message: `Nombre "${num}" present dans la cible mais absent du source`,
        });
      }
    }

    return warnings;
  }

  /**
   * SDD §11.4 : Compare les balises de markup entre source et cible.
   * Markdown **_[]() + HTML <em><strong><a>.
   */
  private compareMarkup(
    source: string[],
    target: string[],
  ): ConsistencyReport["warnings"] {
    const sourceText = source.join(" ");
    const targetText = target.join(" ");

    const checks: Array<{
      name: string;
      open: RegExp;
      close?: RegExp;
    }> = [
      { name: "** (gras)", open: /\*\*/g },
      { name: "_ (italique)", open: /(?<!\*)_(?!\*)/g },
      { name: "[ (lien)", open: /\[/g },
      { name: "](", open: /\]\(/g },
      { name: "<em>", open: /<em>/gi, close: /<\/em>/gi },
      { name: "<strong>", open: /<strong>/gi, close: /<\/strong>/gi },
      { name: "<a>", open: /<a\b[^>]*>/gi, close: /<\/a>/gi },
    ];

    const warnings: ConsistencyReport["warnings"] = [];

    for (const check of checks) {
      const sourceOpen = (
        sourceText.match(check.open) || []
      ).length;
      const targetOpen = (
        targetText.match(check.open) || []
      ).length;

      let sourceClose = 0;
      let targetClose = 0;
      if (check.close) {
        sourceClose = (sourceText.match(check.close) || []).length;
        targetClose = (targetText.match(check.close) || []).length;
      }

      if (sourceOpen !== targetOpen || sourceClose !== targetClose) {
        warnings.push({
          severity: "low",
          message: `Balises "${check.name}" : ${sourceOpen}/${sourceClose} source, ${targetOpen}/${targetClose} cible`,
        });
      }
    }

    return warnings;
  }

  /**
   * Compte le nombre total d'éléments de markup dans un texte.
   */
  private countMarkupElements(text: string): number {
    let count = 0;
    count += (text.match(/\*\*/g) || []).length;
    count += (text.match(/(?<!\*)_(?!\*)/g) || []).length;
    count += (text.match(/\[/g) || []).length;
    count += (text.match(/\]\(/g) || []).length;
    count += (text.match(/<em>/gi) || []).length;
    count += (text.match(/<\/em>/gi) || []).length;
    count += (text.match(/<strong>/gi) || []).length;
    count += (text.match(/<\/strong>/gi) || []).length;
    count += (text.match(/<a\b[^>]*>/gi) || []).length;
    count += (text.match(/<\/a>/gi) || []).length;
    return count;
  }
}

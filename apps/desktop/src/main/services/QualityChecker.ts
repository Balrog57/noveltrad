import type {
  QualityReport,
  LexiconEntry,
  ConsistencyReport,
} from "@shared/types/index.js";
import { HallucinationDetector } from "./HallucinationDetector.js";

export class QualityChecker {
  private hallucinationDetector: HallucinationDetector;

  constructor(hallucinationDetector?: HallucinationDetector) {
    this.hallucinationDetector =
      hallucinationDetector ?? new HallucinationDetector();
  }

  async evaluate(
    source: string,
    target: string,
    _lexicon: LexiconEntry[],
    consistencyReport?: ConsistencyReport,
  ): Promise<QualityReport> {
    // Version simplifiee sans IA pour le MVP : scoring heuristique
    const sourceLen = source.length;
    const targetLen = target.length;
    const lengthRatio = sourceLen === 0 ? 1 : targetLen / sourceLen;
    const lengthScore = Math.max(
      0,
      Math.min(100, 100 - Math.abs(lengthRatio - 1) * 100),
    );

    const grammarScore = this.checkGrammar(target);
    const styleScore = this.checkStyle(target);

    // SDD §12.6 : score d'hallucination via HallucinationDetector
    let hallucinationScore: number;
    try {
      const hReport = this.hallucinationDetector.detect(
        source,
        target,
        "source",
        "target",
      );
      hallucinationScore = hReport.score ?? 95;
    } catch {
      hallucinationScore = 95;
    }

    // SDD §12.5 : cohérence via ConsistencyReport
    const consistencyScore =
      consistencyReport && sourceLen > 0 && targetLen > 0
        ? consistencyReport.globalScore
        : sourceLen > 0 && targetLen > 0
          ? 90
          : 0;

    const scores = {
      consistency: consistencyScore,
      grammar: grammarScore,
      fluency: styleScore,
      style: styleScore,
      lexicon: 90,
      hallucination: hallucinationScore,
      length: lengthScore,
      dialogue: 90,
    };

    const globalScore = Math.round(
      scores.consistency * 0.25 +
        scores.grammar * 0.15 +
        scores.fluency * 0.2 +
        scores.style * 0.15 +
        scores.lexicon * 0.15 +
        scores.hallucination * 0.05 +
        scores.length * 0.03 +
        scores.dialogue * 0.02,
    );

    return { ...scores, globalScore, comments: "Scoring heuristique MVP" };
  }

  private checkGrammar(text: string): number {
    const errors = [
      /\bil\s+sont\b/gi,
      /\bj'ai\s+all[eé]\b/gi,
      /[a-zA-ZÀ-ÿ][?!:;]/g,
    ];
    let penalty = 0;
    for (const pattern of errors) {
      const matches = text.match(pattern);
      if (matches) {penalty += matches.length * 5;}
    }
    return Math.max(0, 100 - penalty);
  }

  private checkStyle(text: string): number {
    const awkwardPatterns = [
      /\bliterally\b/gi,
      /\bvery\s+very\b/gi,
      /\bhe\s+said\s+he\b/gi,
    ];
    let penalty = 0;
    for (const pattern of awkwardPatterns) {
      const matches = text.match(pattern);
      if (matches) {penalty += matches.length * 10;}
    }
    return Math.max(0, 100 - penalty);
  }
}

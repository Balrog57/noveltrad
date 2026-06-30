import type { QualityReport, LexiconEntry } from "@shared/types/index.js";

export class QualityChecker {
  async evaluate(
    source: string,
    target: string,
    _lexicon: LexiconEntry[],
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
    const consistencyScore = sourceLen > 0 && targetLen > 0 ? 90 : 0;
    const styleScore = this.checkStyle(target);

    const scores = {
      consistency: consistencyScore,
      grammar: grammarScore,
      fluency: styleScore,
      style: styleScore,
      lexicon: 90,
      hallucination: 95,
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
      if (matches) penalty += matches.length * 5;
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
      if (matches) penalty += matches.length * 10;
    }
    return Math.max(0, 100 - penalty);
  }
}

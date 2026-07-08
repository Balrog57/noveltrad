// v1 — 2026-07-08 (v1.4)
// Prompt système pour l'agent Review (ReviewAgent) — boucle de révision pro.
// Inspiration : honya (Reviewer), LaTeXTrans (Validator).
// Compatible qwen : commence par "You are a helpful assistant."

export const REVIEW_SYSTEM_PROMPT = `You are a helpful assistant. You are a senior literary translator acting as a professional reviewer for a novel translation.

--- INSTRUCTIONS ---
Read the {targetLanguage} translation paragraph by paragraph and identify issues that a professional reviser would catch.

For each issue, provide:
- paragraphIndex: the 0-based index of the paragraph in the translation
- severity: "high" (mistranslation, omission, contradiction), "medium" (fluency, style), "low" (polish)
- category: one of "fidelity", "fluency", "terminology", "style", "consistency"
- original: the exact problematic excerpt from the translation
- suggestion: a concrete improved rendering
- reason: a short justification

Focus on:
- Fidelity: mistranslations, omissions, unjustified additions (counter-sense).
- Terminology: drift from the provided lexicon and novel summary.
- Style: literalism, heavy phrasing, repetitive tics, unnatural dialogue.
- Consistency: pronouns, tense, register, character voice across paragraphs.

Do NOT report cosmetic issues that a proofreader would handle (minor punctuation). Focus on issues a reviser would actually flag.

--- OUTPUT FORMAT ---
Return ONLY a JSON object. Do NOT wrap in markdown code fences. Do NOT add any text before or after.

Schema:
{
  "issues": [
    {
      "paragraphIndex": 0,
      "severity": "high",
      "category": "fidelity",
      "original": "...",
      "suggestion": "...",
      "reason": "..."
    }
  ],
  "summary": "Overall assessment in 1-2 sentences."
}

If the translation is solid, return an empty issues array with a positive summary.`;

/**
 * Construit le prompt utilisateur pour l'agent Review.
 */
export function buildReviewUserPrompt(params: {
  sourceText: string;
  translatedText: string;
  targetLanguage: string;
  novelSummary?: string;
  lexicon?: Array<{ term: string; translation: string }>;
}): string {
  const { sourceText, translatedText, targetLanguage, novelSummary, lexicon } = params;
  const lexBlock =
    lexicon && lexicon.length > 0
      ? `\n--- LEXICON (locked terminology) ---\n${lexicon
          .map((e) => `${e.term} → ${e.translation}`)
          .join("\n")}\n--- END LEXICON ---\n`
      : "";
  const summaryBlock =
    novelSummary && novelSummary.trim().length > 0
      ? `\n--- NOVEL SUMMARY (long-term context) ---\n${novelSummary}\n--- END SUMMARY ---\n`
      : "";

  return `Source text:
${sourceText}

Translation (${targetLanguage}):
${translatedText}
${lexBlock}${summaryBlock}
Reviewer report (JSON):`;
}

// v1 — 2026-06-30
// Prompt système pour l'agent de vérification de cohérence (ConsistencyAgent).
// Compatible qwen : commence par "You are a helpful assistant."
// Sortie JSON structurée : metrics[] + warnings[] + globalScore.

export const CONSISTENCY_SYSTEM_PROMPT = `You are a helpful assistant. You are a translation consistency reviewer.

--- INSTRUCTIONS ---
Compare the source chapter and the translated chapter below.
Detect the following issues:
- Missing or extra paragraphs.
- Missing or extra sentences.
- Missing or extra dialogue lines.
- Names from the lexicon that were altered or omitted.
- Numbers, dates or units that changed.
- Broken Markdown or HTML tags.
- Mismatched opening/closing punctuation.

--- OUTPUT FORMAT ---
Return ONLY a JSON object with this exact schema:
{
  "metrics": [
    { "name": "paragraphs", "source": 254, "target": 253, "ok": false }
  ],
  "warnings": [
    { "severity": "high", "message": "Paragraph 47 is missing in translation" }
  ],
  "globalScore": 0
}
Do NOT wrap in markdown code fences. Do NOT add any text before or after the JSON.`;

/**
 * Construit le prompt utilisateur pour la vérification de cohérence.
 */
export function buildConsistencyUserPrompt(params: {
  sourceText: string;
  translatedText: string;
  lexiconBlock?: string;
}): string {
  const { sourceText, translatedText, lexiconBlock } = params;
  const lexiconSection = lexiconBlock
    ? `\n\nLexicon:\n${lexiconBlock}`
    : "";
  return `Source:\n${sourceText}\n\nTranslation:\n${translatedText}${lexiconSection}`;
}

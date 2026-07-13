// v1 — 2026-06-30
// Prompt système pour l'agent de vérification de cohérence (ConsistencyAgent).
// Compatible qwen : commence par "You are a helpful assistant."
// Sortie JSON structurée : metrics[] + warnings[] + globalScore.

export const CONSISTENCY_SYSTEM_PROMPT = `You are a helpful assistant. You are a translation consistency reviewer with long-term memory.

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

If a "PREVIOUS CHAPTERS CONTEXT" block is provided, ALSO check cross-chapter
coherence against it:
- Character names, pronouns, and genders that drift from earlier chapters.
- Place names and toponyms that changed between chapters.
- Timeline or chronology inconsistencies.
Flag any drift as a warning so it can be corrected downstream.

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
  novelSummary?: string;
}): string {
  const { sourceText, translatedText, lexiconBlock, novelSummary } = params;
  const contextBlock = novelSummary
    ? `--- PREVIOUS CHAPTERS CONTEXT ---\n${novelSummary}\n--- END CONTEXT ---\n\n`
    : "";
  const lexiconSection = lexiconBlock
    ? `\n\nLexicon:\n${lexiconBlock}`
    : "";
  return `${contextBlock}Source:\n${sourceText}\n\nTranslation:\n${translatedText}${lexiconSection}`;
}

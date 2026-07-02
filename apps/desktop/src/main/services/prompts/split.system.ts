// v1 — 2026-06-30
// Prompt système pour l'agent de découpage (SplitAgent).
// Compatible qwen : commence par "You are a helpful assistant."
//
// Note : SDD §25.6 précise que le découpage peut être fait sans appel IA
// (split par doubles retours à la ligne). Ce prompt est conservé pour
// les cas où le découpage IA est préféré (textes sans structure claire).

export const SPLIT_SYSTEM_PROMPT = `You are a helpful assistant. You are a document preprocessor specialized in splitting text into paragraphs.

--- INSTRUCTIONS ---
Split the following chapter text into paragraphs.
Rules:
- Separate by double line breaks.
- Keep Markdown and HTML tags intact.
- Do not merge distinct dialogues.
- Number each paragraph starting from 1.

--- OUTPUT FORMAT ---
Return ONLY a JSON array of objects with fields: indexInChapter, sourceText.
Do NOT wrap in markdown code fences. Do NOT add any text before or after the JSON.`;

/**
 * Construit le prompt utilisateur pour le découpage en paragraphes.
 */
export function buildSplitUserPrompt(params: {
  sourceText: string;
}): string {
  const { sourceText } = params;
  return sourceText;
}

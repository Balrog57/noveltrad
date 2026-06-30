// v1 — 2026-06-30
// Prompt système pour l'agent de pré-traduction (PreTranslateAgent).
// Compatible qwen : commence par "You are a helpful assistant."

export const PRE_TRANSLATE_SYSTEM_PROMPT = `You are a helpful assistant. You are a literal translator specialized in producing accurate first-pass translations.

--- INSTRUCTIONS ---
Translate the following paragraphs literally (word-for-word where possible) into the target language.
Keep names, proper nouns, and punctuation as written.
Preserve the exact paragraph count and order.

--- OUTPUT FORMAT ---
Return ONLY the translated paragraphs, one per line (or separated by double newlines), in the same count and order as the input.
Do NOT wrap in markdown code fences. Do NOT add any text before or after. Do NOT add explanations.`;

/**
 * Construit le prompt utilisateur pour la pré-traduction d'un ensemble de paragraphes.
 */
export function buildPreTranslateUserPrompt(params: {
  sourceText: string;
  sourceLanguage: string;
  targetLanguage: string;
}): string {
  const { sourceText, sourceLanguage, targetLanguage } = params;
  return `Input (${sourceLanguage}):
${sourceText}

Translate to ${targetLanguage} (literal translation, same number of paragraphs):`;
}

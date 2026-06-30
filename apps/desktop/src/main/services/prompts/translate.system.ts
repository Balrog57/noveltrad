// v1 — 2026-06-30
// Prompt système pour l'agent de traduction (TranslateAgent).
// Compatible qwen : commence par "You are a helpful assistant."

export const TRANSLATE_SYSTEM_PROMPT = `You are a helpful assistant. You are an expert literary translator.

--- INSTRUCTIONS ---
Translate the source text into the target language while preserving the literary style, tone, and nuance of the original.
Apply the provided lexicon entries strictly: if a term appears in the lexicon, use its exact translation. Locked terms must NOT be modified.
Use the translation memory examples as reference for consistency with previously translated passages.

--- OUTPUT FORMAT ---
Return ONLY the translated paragraph text. Do NOT wrap in markdown code fences. Do NOT add any text before or after. Do NOT add explanations, notes, or commentary.`;

/**
 * Construit le prompt utilisateur pour la traduction d'un paragraphe.
 */
export function buildTranslateUserPrompt(params: {
  sourceText: string;
  sourceLanguage: string;
  targetLanguage: string;
  lexiconBlock: string;
  memoryBlock: string;
  ragBlock?: string;
}): string {
  const {
    sourceText,
    sourceLanguage,
    targetLanguage,
    lexiconBlock,
    memoryBlock,
    ragBlock,
  } = params;
  return `${lexiconBlock}${memoryBlock}${ragBlock ?? ""}Source (${sourceLanguage}):
${sourceText}

Translate to ${targetLanguage}:`;
}

// v1 — 2026-06-30
// Prompt système pour l'agent de polissage final (PolishAgent).
// Compatible qwen : commence par "You are a helpful assistant."

export const POLISH_SYSTEM_PROMPT = `You are a helpful assistant. You are an expert editor specialized in final editorial polishing.

--- INSTRUCTIONS ---
Perform a final editorial pass on the following text.
Ensure natural rhythm, consistent dialogue quality, and no artificial language tics.
Smooth any remaining rough edges while preserving the author's voice and intent.

--- OUTPUT FORMAT ---
Return ONLY the polished text. Do NOT wrap in markdown code fences. Do NOT add any text before or after. Do NOT add explanations.`;

/**
 * Construit le prompt utilisateur pour le polissage final.
 */
export function buildPolishUserPrompt(params: {
  text: string;
  targetLanguage: string;
}): string {
  const { text, targetLanguage } = params;
  return `Text to polish (${targetLanguage}):
${text}

Polished text:`;
}

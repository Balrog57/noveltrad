// v1 — 2026-06-30
// Prompt système pour l'agent d'amélioration stylistique (StyleAgent).
// Compatible qwen : commence par "You are a helpful assistant."

export const STYLE_SYSTEM_PROMPT = `You are a helpful assistant. You are an expert literary editor specialized in improving prose flow and naturalness.

--- INSTRUCTIONS ---
Rewrite the following text to improve flow, remove awkward phrasing, and eliminate literal translation artifacts.
Keep the original meaning and genre tone. Maintain the same level of formality.
Do not add or remove content — only improve the expression.

If a "PREVIOUS CHAPTERS CONTEXT" block is provided, use it to keep the style,
character voices, and narrative register consistent with earlier chapters. Do
not introduce stylistic shifts that would break continuity with prior chapters.

--- OUTPUT FORMAT ---
Return ONLY the rewritten text. Do NOT wrap in markdown code fences. Do NOT add any text before or after. Do NOT add explanations.`;

/**
 * Construit le prompt utilisateur pour l'amélioration stylistique.
 */
export function buildStyleUserPrompt(params: {
  text: string;
  targetLanguage: string;
  novelSummary?: string;
}): string {
  const { text, targetLanguage, novelSummary } = params;
  const contextBlock = novelSummary
    ? `--- PREVIOUS CHAPTERS CONTEXT ---\n${novelSummary}\n--- END CONTEXT ---\n\n`
    : "";
  return `${contextBlock}Text to improve (${targetLanguage}):
${text}

Rewritten text:`;
}

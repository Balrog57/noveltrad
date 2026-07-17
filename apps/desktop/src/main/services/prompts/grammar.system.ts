// v1 — 2026-06-30
// Prompt système pour l'agent de correction grammaticale (GrammarAgent).
// Compatible qwen : commence par "You are a helpful assistant."

export const GRAMMAR_SYSTEM_PROMPT = `You are a helpful assistant. You are an expert proofreader specializing in grammar, spelling, and punctuation correction.

--- INSTRUCTIONS ---
Review the provided text and correct any grammar, spelling, and punctuation errors.
Preserve the original meaning, tone, and formatting. Do not rewrite or rephrase — only fix errors.
Do not modify proper nouns, character names, or locked terminology.

If a "PREVIOUS CHAPTERS CONTEXT" block is provided, use it to keep tense and
pronoun usage consistent with earlier chapters (e.g. narrative tense, character
gender/pronouns), and fix any drift you detect.

--- OUTPUT FORMAT ---
Return ONLY the corrected text. Do NOT wrap in markdown code fences. Do NOT add any text before or after. Do NOT add explanations.`;

/**
 * Construit le prompt utilisateur pour la correction grammaticale.
 */
export function buildGrammarUserPrompt(params: {
  text: string;
  targetLanguage: string;
  novelSummary?: string;
}): string {
  const { text, targetLanguage, novelSummary } = params;
  const contextBlock = novelSummary
    ? `--- PREVIOUS CHAPTERS CONTEXT ---\n${novelSummary}\n--- END CONTEXT ---\n\n`
    : "";
  return `${contextBlock}Text to proofread (${targetLanguage}):
${text}

Corrected text:`;
}

/**
 * Spécification consommée par TextRefineAgent (P2-5 refactor). Regroupe
 * l'identité + le prompt du stage grammar en un objet unique.
 */
import type { RefineSpec } from "../agents/TextRefineAgent.js";
export const GRAMMAR_SPEC: RefineSpec = {
  id: "grammar",
  name: "Grammaire",
  stage: "grammar",
  systemPrompt: GRAMMAR_SYSTEM_PROMPT,
  buildUserPrompt: buildGrammarUserPrompt,
};

// v3 — 2026-07-22
// Prompt système unifié pour l'agent Proofreader (ProofreaderAgent).
// Fusionne les 3 anciens stages grammar + style + polish en un seul passage
// éditorial, conformément à la simplification v3 (REFACTOR_PLAN_V3.md Phase 1).
// Compatible qwen : commence par "You are a helpful assistant."

export const PROOFREAD_SYSTEM_PROMPT = `You are a helpful assistant. You are an expert literary editor and proofreader specialized in refining translations into natural, publishable prose.

--- INSTRUCTIONS ---
Perform a comprehensive editorial pass on the following text in three areas at once:

1. GRAMMAR & MECHANICS: correct any grammar, spelling, and punctuation errors. Uniformize quotation marks, ellipses, and spacing. Remove double spaces and AI artifacts.

2. STYLE & FLOW: improve rhythm and naturalness, remove awkward phrasing and literal translation artifacts. Keep the original meaning, genre tone, and level of formality. Do not add or remove content — only improve the expression.

3. FINAL POLISH: ensure consistent dialogue quality, no artificial language tics, and smooth remaining rough edges. Preserve the author's voice and intent.

Do not modify proper nouns, character names, or locked terminology. Do not rewrite or rephrase beyond what is needed for the fixes above.

If a "PREVIOUS CHAPTERS CONTEXT" block is provided, use it to keep tense, pronouns, character voices, and narrative register consistent with earlier chapters. Fix any drift you detect.

--- OUTPUT FORMAT ---
Return ONLY the refined text. Do NOT wrap in markdown code fences. Do NOT add any text before or after. Do NOT add explanations.`;

/**
 * Construit le prompt utilisateur pour le passage éditorial unifié (v3).
 */
export function buildProofreadUserPrompt(params: {
  text: string;
  targetLanguage: string;
  novelSummary?: string;
}): string {
  const { text, targetLanguage, novelSummary } = params;
  const contextBlock = novelSummary
    ? `--- PREVIOUS CHAPTERS CONTEXT ---\n${novelSummary}\n--- END CONTEXT ---\n\n`
    : "";
  return `${contextBlock}Text to proofread and refine (${targetLanguage}):
${text}

Refined text:`;
}

/**
 * Spécification consommée par ProofreaderAgent (TextRefineAgent + ce spec).
 * v3 : fusionne grammar + style + polish en un seul stage "proofread".
 */
import type { RefineSpec } from "../agents/TextRefineAgent.js";
export const PROOFREAD_SPEC: RefineSpec = {
  id: "proofread",
  name: "Proofreader",
  stage: "proofread",
  systemPrompt: PROOFREAD_SYSTEM_PROMPT,
  buildUserPrompt: buildProofreadUserPrompt,
};

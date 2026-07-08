// v1 — 2026-07-08 (v1.4)
// Prompt système pour le SummarizerAgent (cohérence cross-chapitre).
// Inspiration : LaTeXTrans (Summarizer), TransAgents.
// Compatible qwen : commence par "You are a helpful assistant."

export const SUMMARIZER_SYSTEM_PROMPT = `You are a helpful assistant. You maintain a running summary of a long-form novel to ensure cross-chapter consistency.

--- INSTRUCTIONS ---
Produce two outputs:
1. chapterSummary: a concise summary of THIS chapter (~150 words). Include key events, named entities introduced or referenced, tone shifts, and unresolved plot threads.
2. novelSummary: an UPDATED overall novel summary that merges the previous summary with this chapter's new information. Keep it under ~500 words. Drop stale detail but preserve ALL named entities once established (characters, places, sects, items, techniques).

Be factual and neutral. Do not speculate beyond the text provided.

--- OUTPUT FORMAT ---
Return ONLY a JSON object. Do NOT wrap in markdown code fences. Do NOT add any text before or after.

{
  "chapterSummary": "...",
  "novelSummary": "..."
}`;

/**
 * Construit le prompt utilisateur pour le SummarizerAgent.
 */
export function buildSummarizerUserPrompt(params: {
  sourceText: string;
  translatedText: string;
  novelSummary?: string;
}): string {
  const { sourceText, translatedText, novelSummary } = params;
  const prevBlock =
    novelSummary && novelSummary.trim().length > 0
      ? novelSummary
      : "(no previous summary — this is the first chapter)";

  return `Previous novel summary:
${prevBlock}

This chapter (source):
${sourceText}

This chapter (translated):
${translatedText}

Summary (JSON):`;
}

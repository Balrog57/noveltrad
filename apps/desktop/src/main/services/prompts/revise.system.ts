// v1 — 2026-07-08 (v1.4)
// Prompt système pour l'agent Revise (ReviseAgent) — applique les corrections
// du ReviewReport via réécriture LLM ciblée.
// Compatible qwen : commence par "You are a helpful assistant."

export const REVISE_SYSTEM_PROMPT = `You are a helpful assistant. You are a senior literary translator applying targeted corrections to a novel translation.

--- INSTRUCTIONS ---
Apply the reviewer's suggestions below to the translated text. Integrate them naturally into the flow; do not introduce new errors and do not alter passages that the reviewer did not flag.

Rules:
- Preserve the paragraph structure exactly (one paragraph per line, same count).
- Preserve all names and locked terminology.
- If a suggestion contradicts the source meaning, keep the closest faithful rendering.
- Do not add commentary, notes, or explanations in the output.

--- OUTPUT FORMAT ---
Return ONLY the revised text, one paragraph per line. Do NOT wrap in markdown code fences. Do NOT add any text before or after.`;

/**
 * Construit le prompt utilisateur pour l'agent Revise.
 */
export function buildReviseUserPrompt(params: {
  translatedText: string;
  reviewIssues: Array<{
    paragraphIndex: number;
    severity: string;
    category: string;
    original: string;
    suggestion: string;
    reason: string;
  }>;
}): string {
  const { translatedText, reviewIssues } = params;
  const issuesBlock =
    reviewIssues.length > 0
      ? reviewIssues
          .map(
            (i) =>
              `- Paragraph ${i.paragraphIndex} [${i.severity}/${i.category}]: "${i.original}" → "${i.suggestion}" (${i.reason})`,
          )
          .join("\n")
      : "- (no issues flagged — return the text unchanged)";

  return `Translated text:
${translatedText}

Corrections to apply:
${issuesBlock}

Revised text:`;
}

// v1 — 2026-06-30
// Prompt système pour l'agent de formatage export (ExportAgent).
// Compatible qwen : commence par "You are a helpful assistant."
//
// Note : SDD §25.6 précise que l'export peut être fait sans appel IA
// (formatage par règles). Ce prompt est conservé pour les formats
// complexes (EPUB, PDF) où une mise en page IA peut être utile.

export const EXPORT_SYSTEM_PROMPT = `You are a helpful assistant. You are a document formatter.

--- INSTRUCTIONS ---
Assemble the translated paragraphs below into a clean document.
Include the chapter title and preserve paragraph breaks.
Format the output according to the requested format type.

--- OUTPUT FORMAT ---
Return ONLY the formatted document content.
Do NOT wrap in markdown code fences. Do NOT add any text before or after.`;

/**
 * Construit le prompt utilisateur pour le formatage d'export.
 */
export function buildExportUserPrompt(params: {
  chapterTitle: string;
  translatedText: string;
  format: string;
}): string {
  const { chapterTitle, translatedText, format } = params;
  return `Format: ${format}\nTitle: ${chapterTitle}\nParagraphs:\n${translatedText}`;
}

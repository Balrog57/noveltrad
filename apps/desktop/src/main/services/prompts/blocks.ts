import type { LexiconEntry } from "@shared/types/index.js";

/**
 * Blocs de prompt réutilisables par plusieurs agents.
 *
 * P2-6 refactor : `buildLexiconBlock` était copié-collé à l'identique dans
 * TranslateAgent, ConsistencyAgent et LexiconAgent. Centralisation ici pour
 * garantir qu'ils restent en sync (format, marquage LOCKED, separators).
 */

/**
 * Construit le bloc de contexte lexique injecté dans les prompts LLM.
 *
 * Format :
 *   --- LEXICON ---
 *   - term → translation
 *   - lockedTerm → translation (LOCKED)
 *   --- END LEXICON ---
 *
 * @param entries Entrées du lexique (typiquement déjà filtrées par chapitre).
 * @returns Le bloc formaté, ou chaîne vide si pas d'entrées.
 */
export function buildLexiconBlock(entries?: LexiconEntry[] | null): string {
  if (!entries?.length) {return "";}
  const lines = entries.map(
    (e) => `- ${e.term} → ${e.translation}${e.locked ? " (LOCKED)" : ""}`,
  );
  return `--- LEXICON ---\n${lines.join("\n")}\n--- END LEXICON ---\n\n`;
}

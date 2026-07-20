/**
 * WS-3 (clean architecture) : extrait de AiRouter.isEthicalRefusal.
 *
 * Fonction PURE (aucun état). Détecte si le texte est un refus éthique du LLM
 * (refus de traduction, contenu inapproprié, etc.).
 */
const REFUSAL_PATTERNS: ReadonlyArray<RegExp> = [
  /^I cannot/i,
  /^I('|’)m sorry/i,
  /^I apologize/i,
  /^As an AI/i,
  /^抱歉/,
  /^无法/,
  /^我不能/,
];

export function isEthicalRefusal(text: string): boolean {
  const trimmed = text.trim();
  return REFUSAL_PATTERNS.some((pattern) => pattern.test(trimmed));
}

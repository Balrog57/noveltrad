/**
 * Axe 1a (clean architecture followup) : extrait la politique de branching QA
 * du WorkflowRunner.runStep (SDD §7.1).
 *
 * ## Approche : policy holder immutable
 *
 * Le policy ne mute RIEN — il prend l'état courant en input et retourne une
 * décision. Le runner conserve la responsabilité des mutations (pause,
 * retryWeakestStep, jobRepo.updateStep) mais délègue le choix.
 *
 * Bénéfices :
 *   - La politique est testable ISOLÉMENT (cf. tests/unit/qa-branch-policy
 *     .spec.ts) — fini les 70 LOC inline non couverts par les tests
 *     workflow-branching existants (qui mockent l'engine complet).
 *   - Les seuils (threshold, marge intermédiaire de 20, maxRetries) sont
 *     centralisés et explicites.
 *   - Le runner runStep se simplifie : un switch sur la décision au lieu
 *     d'un if/else à 3 branches entrelavé avec mutations DB.
 */

/**Décision retournée par le policy après exécution du QA agent. */
export type QaDecision =
  /** Score ≥ threshold : continuer normalement vers le stage suivant. */
  | { action: "continue" }
  /** Score intermédiaire [threshold-20, threshold) et retryCount ≤ max :
   *  retry le step le plus faible. */
  | { action: "retryWeakest" }
  /** Score intermédiaire mais retryCount > max : pause + reason spécifique. */
  | { action: "pause"; reason: "max_qa_retries_exceeded" }
  /** Score trop bas (< threshold - 20) : pause immédiate. */
  | { action: "pause"; reason: "low_score" };

/**
 * Marge entre "pause immédiate" et "retry weakest". Si score ∈
 * [threshold - BRANCH_MARGIN, threshold), on tente un retry.
 */
export const QA_BRANCH_MARGIN = 20;

/**
 * Calcule la décision de branching QA étant donné le score, le seuil et le
 * compteur de retries courant.
 *
 * @param score       Score du QA agent (output.score ?? 0).
 * @param threshold   Seuil de qualité (settings.qualityThreshold, défaut 70).
 * @param retryCount  Nb de retries QA déjà faits pour ce chapitre (0-based).
 * @param maxRetries  Cap de retries (settings.maxQaRetries, défaut 3).
 */
export function decideQaBranch(
  score: number,
  threshold: number,
  retryCount: number,
  maxRetries: number,
): QaDecision {
  if (score >= threshold) {
    return { action: "continue" };
  }
  // Score en dessous du seuil.
  if (score >= threshold - QA_BRANCH_MARGIN) {
    // Zone intermédiaire : retry si on n'a pas dépassé le cap.
    if (retryCount > maxRetries) {
      return { action: "pause", reason: "max_qa_retries_exceeded" };
    }
    return { action: "retryWeakest" };
  }
  // Score trop bas.
  return { action: "pause", reason: "low_score" };
}

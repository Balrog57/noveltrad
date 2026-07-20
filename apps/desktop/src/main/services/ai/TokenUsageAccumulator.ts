import type { TokenUsage } from "@shared/types/index.js";

/**
 * WS-3 (clean architecture) : extrait de AiRouter ( accumulateur d'usage ).
 *
 * SDD §3.8 : accumulateur d'usage de tokens pour le step courant. Reset via
 * `reset()` au début de chaque step (WorkflowEngine.runStep), lu via
 * `getAndReset()` à la fin pour remplir step.tokensIn/Out.
 *
 * Isoler cette responsabilité dans sa propre classe la rend testable
 * indépendamment (cf. ai-usage.spec.ts) et clarifie le rôle de AiRouter
 * (qui devient un router, pas un accumulateur).
 */
export class TokenUsageAccumulator {
  private usage: TokenUsage = {
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0,
  };

  /** Réinitialise l'accumulateur (appelé en début de step). */
  reset(): void {
    this.usage = { promptTokens: 0, completionTokens: 0, totalTokens: 0 };
  }

  /**
   * Retourne l'usage accumulé depuis le dernier `reset()` et le réinitialise.
   * Retourne `undefined` si aucun appel n'a été fait (tous les champs à 0),
   * pour rester cohérent avec step.tokensIn/Out optionnels.
   */
  getAndReset(): TokenUsage | undefined {
    const u = this.usage;
    const empty = u.promptTokens === 0 && u.completionTokens === 0;
    this.reset();
    return empty ? undefined : u;
  }

  /**
   * Additionne un usage à l'accumulateur courant.
   * Ignore `undefined` silencieusement.
   */
  add(usage?: TokenUsage): void {
    if (!usage) {
      return;
    }
    this.usage.promptTokens += usage.promptTokens;
    this.usage.completionTokens += usage.completionTokens;
    this.usage.totalTokens += usage.totalTokens;
  }
}

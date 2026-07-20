/**
 * WS-3 (clean architecture) : extrait de AiRouter ( coût par modèle ).
 *
 * SDD §3.8 : coûts par modèle (clé = model id). Vide = pas de suivi
 * (Ollama local/gratuit par défaut). Isoler dans sa propre classe clarifie
 * le rôle de AiRouter (routing) vs l'accounting de coûts.
 */
export interface ModelCost {
  costPerInputToken: number;
  costPerOutputToken: number;
}

export class CostEstimator {
  private modelCosts: Record<string, ModelCost> = {};

  /** Configure les coûts par modèle (lus depuis les settings). */
  setModelCosts(costs: Record<string, ModelCost>): void {
    this.modelCosts = costs ?? {};
  }

  /**
   * Estime le coût USD d'un appel.
   * @returns 0 si le modèle n'est pas configuré (local/gratuit) ou si pas de tokens.
   */
  estimateCost(
    modelId: string,
    inputTokens: number,
    outputTokens: number,
  ): number {
    const cost = this.modelCosts[modelId];
    if (!cost) {
      return 0;
    }
    return (
      (inputTokens / 1000) * cost.costPerInputToken +
      (outputTokens / 1000) * cost.costPerOutputToken
    );
  }
}

import type {
  AgentInput,
  AgentOutput,
  WorkflowStage,
} from "@shared/types/index.js";
import type { z } from "zod";

/**
 * Classe de base abstraite pour tous les agents du workflow NovelTrad.
 *
 * Chaque agent concret étend cette classe et doit implémenter `execute()`.
 * Les sous-classes peuvent optionnellement définir `outputSchema` pour
 * activer la validation automatique de la sortie via Zod.
 *
 * SDD §8.13 — Agent I/O validation
 */
export abstract class Agent {
  abstract readonly id: string;
  abstract readonly name: string;
  abstract readonly stage: WorkflowStage;
  readonly defaultModel?: string;

  /** Schéma Zod optionnel pour valider l'entrée (non utilisé par le runner pour l'instant) */
  readonly inputSchema?: z.ZodSchema;

  /** Schéma Zod optionnel pour valider la sortie de l'agent */
  readonly outputSchema?: z.ZodSchema;

  abstract execute(input: AgentInput): Promise<AgentOutput>;

  /**
   * Valide la sortie brute de l'agent via `outputSchema`.
   *
   * - Si aucun `outputSchema` n'est défini, retourne `raw` tel quel
   *   (casté en `AgentOutput`).
   * - Si un `outputSchema` est défini, parse `raw` avec Zod.
   *   Lève une `ZodError` si la sortie est invalide — le catch est géré
   *   par `WorkflowEngine.runStep()` qui loggue un avertissement et
   *   utilise la sortie brute comme fallback.
   */
  validateOutput(raw: unknown): AgentOutput {
    if (!this.outputSchema) {
      return raw as AgentOutput;
    }
    return this.outputSchema.parse(raw) as AgentOutput;
  }
}

/**
 * Configuration d'un agent (provider + modèle).
 *
 * Conservée en tant qu'interface indépendante pour ne pas polluer la
 * classe de base avec des détails de configuration.
 */
export interface AgentConfig {
  providerId: string;
  model: string;
  temperature?: number;
  maxTokens?: number;
}

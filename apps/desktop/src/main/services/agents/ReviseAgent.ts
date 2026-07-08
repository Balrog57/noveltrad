// v1 — 2026-07-08 (v1.4)
// Agent Revise : applique les corrections du ReviewReport via réécriture LLM
// ciblée. Calqué sur GrammarAgent, mais consomme le reviewReport du stage
// précédent (injecté par le WorkflowEngine via options).

import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  ReviewIssue,
  ReviewReport,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import {
  REVISE_SYSTEM_PROMPT,
  buildReviseUserPrompt,
} from "../prompts/revise.system.js";
import { reviseOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

export class ReviseAgent extends Agent {
  readonly id = "revise";
  readonly name = "Correcteur";
  readonly stage = "revise" as const;
  readonly outputSchema = reviseOutputSchema;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
  ) {
    super();
  }

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? "";
    const reviewReport = (input.options?.reviewReport as ReviewReport | undefined) ?? {
      issues: [],
      summary: "",
    };

    // Si pas d'issue à appliquer, on retourne le texte tel quel (économie de coût)
    if (!reviewReport.issues || reviewReport.issues.length === 0) {
      logger.info("[ReviseAgent] Aucune correction à appliquer, texte inchangé");
      return { text };
    }

    const userPrompt = buildReviseUserPrompt({
      translatedText: text,
      reviewIssues: reviewReport.issues as ReviewIssue[],
    });

    try {
      const response = await this.aiRouter.chat(this.config.providerId, [
        { role: "system", content: REVISE_SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ]);

      // Détection de refus éthique
      if (this.aiRouter.isEthicalRefusal(response)) {
        logger.warn(
          "[ReviseAgent] Refus éthique détecté — conservation du texte d'entrée",
        );
        return {
          text,
          metadata: { ethicalRefusal: true },
        };
      }

      return { text: response.trim() };
    } catch (err) {
      logger.warn("[ReviseAgent] LLM revise failed, conserving input text", {
        error: (err as Error).message,
      });
      return { text };
    }
  }
}

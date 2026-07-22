import type { WorkflowStage } from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import { TranslateAgent } from "./TranslateAgent.js";
import { LexiconAgent } from "./LexiconAgent.js";
import { ProofreaderAgent } from "./ProofreaderAgent.js";
import { ValidatorAgent } from "./ValidatorAgent.js";
import type { LexiconEngine } from "../LexiconEngine.js";
import type { TranslationMemoryEngine } from "../TranslationMemoryEngine.js";
import type { ConsistencyChecker } from "../ConsistencyChecker.js";
import type { QualityChecker } from "../QualityChecker.js";

/**
 * v3 : factory simplifiée pour le pipeline 4-stages.
 *
 * Crée l'agent approprié pour un stage donné. Les anciens stages (split,
 * pre_translate, consistency, grammar, style, polish, review, revise, qa,
 * export) ont été supprimés — leurs agents et prompts ne sont plus référencés.
 *
 * Le switch couvre uniquement les 4 stages v3 : translate, proofread, glossary,
 * validate. Tout autre stage lève une erreur explicite.
 */
export interface AgentFactoryServices {
  aiRouter: AiRouter;
  lexiconEngine: LexiconEngine;
  tmEngine: TranslationMemoryEngine;
  consistencyChecker: ConsistencyChecker;
  qualityChecker: QualityChecker;
}

export class AgentFactory {
  constructor(private services: AgentFactoryServices) {}

  create(stage: WorkflowStage, config: AgentConfig): Agent {
    switch (stage) {
      case "translate":
        return new TranslateAgent(
          config,
          this.services.aiRouter,
          this.services.tmEngine,
        );
      case "proofread":
        // v3 : fusionne grammar + style + polish en un seul passage éditorial.
        return new ProofreaderAgent(config, this.services.aiRouter);
      case "glossary":
        return new LexiconAgent(config, this.services.lexiconEngine, this.services.aiRouter);
      case "validate":
        // v3 : fusionne consistency + qa en une seule évaluation de qualité.
        return new ValidatorAgent(
          config,
          this.services.aiRouter,
          this.services.qualityChecker,
          this.services.consistencyChecker,
        );
      default:
        throw new Error(`Stage inconnu (v3 pipeline 4-stages) : ${stage}`);
    }
  }
}

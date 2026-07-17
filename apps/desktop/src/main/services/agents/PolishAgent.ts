import type { AgentConfig } from "./Agent.js";
import type { AiRouter } from "../AiRouter.js";
import { TextRefineAgent } from "./TextRefineAgent.js";
import { POLISH_SPEC } from "../prompts/polish.system.js";

/**
 * P2-5 refactor : PolishAgent est désormais un thin wrapper autour de
 * TextRefineAgent. Cf. GrammarAgent pour la rationale de conservation.
 */
export class PolishAgent extends TextRefineAgent {
  constructor(config: AgentConfig, aiRouter: AiRouter) {
    super(config, aiRouter, POLISH_SPEC);
  }
}

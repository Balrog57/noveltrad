import type { AgentConfig } from "./Agent.js";
import type { AiRouter } from "../AiRouter.js";
import { TextRefineAgent } from "./TextRefineAgent.js";
import { STYLE_SPEC } from "../prompts/style.system.js";

/**
 * P2-5 refactor : StyleAgent est désormais un thin wrapper autour de
 * TextRefineAgent. Cf. GrammarAgent pour la rationale de conservation.
 */
export class StyleAgent extends TextRefineAgent {
  constructor(config: AgentConfig, aiRouter: AiRouter) {
    super(config, aiRouter, STYLE_SPEC);
  }
}

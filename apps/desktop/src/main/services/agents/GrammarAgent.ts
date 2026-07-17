import type { AgentConfig } from "./Agent.js";
import type { AiRouter } from "../AiRouter.js";
import { TextRefineAgent } from "./TextRefineAgent.js";
import { GRAMMAR_SPEC } from "../prompts/grammar.system.js";

/**
 * P2-5 refactor : GrammarAgent est désormais un thin wrapper autour de
 * TextRefineAgent. Conservé pour :
 *   - les tests qui l'instancient directement (agents.spec.ts)
 *   - le worker threads (agent-worker.ts) qui l'importe paresseusement
 *   - la compatibilité des plugins tiers qui pourraient l'étendre
 *
 * Toute la logique vit dans TextRefineAgent.
 */
export class GrammarAgent extends TextRefineAgent {
  constructor(config: AgentConfig, aiRouter: AiRouter) {
    super(config, aiRouter, GRAMMAR_SPEC);
  }
}

import type { AgentConfig } from "./Agent.js";
import type { AiRouter } from "../AiRouter.js";
import { TextRefineAgent } from "./TextRefineAgent.js";
import { PROOFREAD_SPEC } from "../prompts/proofread.system.js";

/**
 * v3 (REFACTOR_PLAN_V3.md Phase 1) : ProofreaderAgent fusionne les anciens
 * stages grammar + style + polish en un seul passage éditorial.
 *
 * Implémentation déléguée à TextRefineAgent (flux identique : build prompt →
 * resolvePrompt → chatWithChunking → détection refus éthique). Seul le
 * PROOFREAD_SPEC diffère (prompt unifié en 3 axes : mécanique, style, polish).
 *
 * Conservé comme classe nommée (plutôt que TextRefineAgent inline) pour :
 *   - la lisibilité du switch AgentFactory
 *   - les tests qui l'instancient directement
 *   - l'inspecteur d'agents côté renderer (label "Proofreader")
 */
export class ProofreaderAgent extends TextRefineAgent {
  constructor(config: AgentConfig, aiRouter: AiRouter) {
    super(config, aiRouter, PROOFREAD_SPEC);
  }
}

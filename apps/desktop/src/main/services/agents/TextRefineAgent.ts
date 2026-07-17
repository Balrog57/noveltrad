import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput, WorkflowStage } from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import { textOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

/**
 * Paramètres communs aux trois stages de raffinement de texte
 * (grammar / style / polish). Identique à la signature des builders
 * `build{Grammar,Style,Polish}UserPrompt`.
 */
export interface RefinePromptOpts {
  text: string;
  targetLanguage: string;
  novelSummary?: string;
}

/**
 * Spécification d'un stage de raffinement. Les trois stages
 * (grammar / style / polish) ont un flux de contrôle identique ; seuls
 * l'identité (id/name/stage) et les prompts diffèrent. Cette interface
 * capture ce qui varie.
 */
export interface RefineSpec {
  readonly id: string;
  readonly name: string;
  readonly stage: WorkflowStage;
  /** Constante TS du system prompt (fallback si pas d'override DB). */
  readonly systemPrompt: string;
  /** Builder du user prompt. */
  buildUserPrompt(opts: RefinePromptOpts): string;
}

/**
 * Agent générique pour les stages de raffinement de texte paragraphes-
 * indépendants : grammar, style, polish.
 *
 * P2-5 refactor : les trois agents d'origine (GrammarAgent, StyleAgent,
 * PolishAgent) étaient ~55 LOC chacun et identiques à l'identité + prompt
 * près. Cette classe factorise le flux :
 *   1. build du user prompt depuis input.text + options
 *   2. resolvePrompt (override DB optionnel, SDD §25)
 *   3. chatWithChunking (découpage auto des longs chapitres, SDD §3.6b)
 *   4. détection de refus éthique
 *   5. retour du texte raffiné
 *
 * Comportement byte-identique aux agents d'origine.
 */
export class TextRefineAgent extends Agent {
  readonly id: string;
  readonly name: string;
  readonly stage: WorkflowStage;
  readonly outputSchema = textOutputSchema;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
    spec: RefineSpec,
  ) {
    super();
    this.id = spec.id;
    this.name = spec.name;
    this.stage = spec.stage;
    this.spec = spec;
  }

  private spec: RefineSpec;

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? "";
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";
    const novelSummary =
      (input.options?.novelSummary as string | undefined) ?? undefined;

    const userPrompt = this.spec.buildUserPrompt({ text, targetLanguage, novelSummary });

    // P2-11 fix : resolvePrompt uniformise l'override DB (SDD §25) pour tous
    // les agents LLM, pas seulement Translate. Fallback sur la constante TS.
    const systemPrompt = await this.aiRouter.resolvePrompt(
      this.spec.stage,
      this.spec.systemPrompt,
    );

    // SDD §3.6b : chatWithChunking découpe automatiquement le chapitre si le
    // prompt dépasse 50% de la fenêtre de contexte (défaut 32768). Le
    // raffinement est paragraphes-indépendant : découper puis concaténer
    // préserve la structure (1 paragraphe → 1 paragraphe raffiné).
    const response = await this.aiRouter.chatWithChunking(this.config.providerId, [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ]);

    // Détection de refus éthique
    if (this.aiRouter.isEthicalRefusal(response)) {
      logger.warn(
        `[${this.spec.name}Agent] Refus éthique détecté — conservation du texte d'entrée`,
      );
      return {
        text,
        metadata: { ethicalRefusal: true },
      };
    }

    return { text: response.trim() };
  }
}

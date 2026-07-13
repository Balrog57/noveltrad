import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import {
  GRAMMAR_SYSTEM_PROMPT,
  buildGrammarUserPrompt,
} from "../prompts/grammar.system.js";
import { textOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

export class GrammarAgent extends Agent {
  readonly id = "grammar";
  readonly name = "Grammaire";
  readonly stage = "grammar";
  readonly outputSchema = textOutputSchema;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
  ) {
    super();
  }

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? "";
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";
    const novelSummary =
      (input.options?.novelSummary as string | undefined) ?? undefined;

    const userPrompt = buildGrammarUserPrompt({ text, targetLanguage, novelSummary });

    // SDD §3.6b : chatWithChunking découpe automatiquement le chapitre si le
    // prompt dépasse 50% de la fenêtre de contexte (défaut 32768). La
    // correction grammaticale est paragraphes-indépendante : découper puis
    // concaténer préserve la structure (1 paragraphe → 1 paragraphe corrigé).
    const response = await this.aiRouter.chatWithChunking(this.config.providerId, [
      { role: "system", content: GRAMMAR_SYSTEM_PROMPT },
      { role: "user", content: userPrompt },
    ]);

    // Détection de refus éthique
    if (this.aiRouter.isEthicalRefusal(response)) {
      logger.warn(
        `[GrammarAgent] Refus éthique détecté — conservation du texte d'entrée`,
      );
      return {
        text,
        metadata: { ethicalRefusal: true },
      };
    }

    return { text: response.trim() };
  }
}

import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import {
  POLISH_SYSTEM_PROMPT,
  buildPolishUserPrompt,
} from "../prompts/polish.system.js";
import { textOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

export class PolishAgent extends Agent {
  readonly id = "polish";
  readonly name = "Polish";
  readonly stage = "polish";
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

    const userPrompt = buildPolishUserPrompt({ text, targetLanguage, novelSummary });

    // SDD §3.6b : chatWithChunking découpe automatiquement le chapitre long.
    // Le polissage est paragraphes-indépendant : découper puis concaténer
    // préserve la structure.
    const response = await this.aiRouter.chatWithChunking(this.config.providerId, [
      { role: "system", content: POLISH_SYSTEM_PROMPT },
      { role: "user", content: userPrompt },
    ]);

    // Détection de refus éthique
    if (this.aiRouter.isEthicalRefusal(response)) {
      logger.warn(
        `[PolishAgent] Refus éthique détecté — conservation du texte d'entrée`,
      );
      return {
        text,
        metadata: { ethicalRefusal: true },
      };
    }

    return { text: response.trim() };
  }
}

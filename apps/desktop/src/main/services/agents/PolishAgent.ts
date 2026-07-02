import type { Agent, AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import {
  POLISH_SYSTEM_PROMPT,
  buildPolishUserPrompt,
} from "../prompts/polish.system.js";
import { logger } from "../../utils/logger.js";

export class PolishAgent implements Agent {
  readonly id = "polish";
  readonly name = "Polish";
  readonly stage = "polish";

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? "";
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";

    const userPrompt = buildPolishUserPrompt({ text, targetLanguage });

    const response = await this.aiRouter.chat(this.config.providerId, [
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

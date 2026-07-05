import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import {
  STYLE_SYSTEM_PROMPT,
  buildStyleUserPrompt,
} from "../prompts/style.system.js";
import { textOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

export class StyleAgent extends Agent {
  readonly id = "style";
  readonly name = "Style";
  readonly stage = "style";
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

    const userPrompt = buildStyleUserPrompt({ text, targetLanguage });

    const response = await this.aiRouter.chat(this.config.providerId, [
      { role: "system", content: STYLE_SYSTEM_PROMPT },
      { role: "user", content: userPrompt },
    ]);

    // Détection de refus éthique
    if (this.aiRouter.isEthicalRefusal(response)) {
      logger.warn(
        `[StyleAgent] Refus éthique détecté — conservation du texte d'entrée`,
      );
      return {
        text,
        metadata: { ethicalRefusal: true },
      };
    }

    return { text: response.trim() };
  }
}

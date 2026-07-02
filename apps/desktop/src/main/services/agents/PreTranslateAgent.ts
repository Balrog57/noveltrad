import type { Agent, AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  Paragraph,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import {
  PRE_TRANSLATE_SYSTEM_PROMPT,
  buildPreTranslateUserPrompt,
} from "../prompts/pre-translate.system.js";
import { logger } from "../../utils/logger.js";

export class PreTranslateAgent implements Agent {
  readonly id = "pre_translate";
  readonly name = "Pré-traduction";
  readonly stage = "pre_translate";

  private refusalDetected = false;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const sourceLines = paragraphs.map((p) => p.sourceText).join("\n\n");
    const sourceLanguage = (input.options?.sourceLanguage as string) ?? "text";
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";

    this.refusalDetected = false;

    const userPrompt = buildPreTranslateUserPrompt({
      sourceText: sourceLines,
      sourceLanguage,
      targetLanguage,
    });

    const response = await this.aiRouter.chat(this.config.providerId, [
      { role: "system", content: PRE_TRANSLATE_SYSTEM_PROMPT },
      { role: "user", content: userPrompt },
    ]);

    // Détection de refus éthique
    if (this.aiRouter.isEthicalRefusal(response)) {
      this.refusalDetected = true;
      logger.warn(
        `[PreTranslateAgent] Refus éthique détecté — conservation du texte source`,
      );
      const result: Paragraph[] = paragraphs.map((p) => ({
        ...p,
        preTranslatedText: p.sourceText,
      }));
      return {
        paragraphs: result,
        metadata: { ethicalRefusal: true },
      };
    }

    const translatedLines = response
      .split(/\n\n+/)
      .map((t) => t.trim())
      .filter(Boolean);
    const result: Paragraph[] = paragraphs.map((p, i) => ({
      ...p,
      preTranslatedText: translatedLines[i] ?? "",
    }));

    return {
      paragraphs: result,
      metadata: this.refusalDetected ? { ethicalRefusal: true } : undefined,
    };
  }
}

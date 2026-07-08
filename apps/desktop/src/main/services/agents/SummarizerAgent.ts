// v1 — 2026-07-08 (v1.4)
// Agent Summarizer : maintient un résumé incrémental du roman pour la cohérence
// cross-chapitre. Agent TRANSVERSE : n'est PAS dans STAGES, appelé par le
// WorkflowEngine après l'export réussi d'un chapitre (cf. §7.13).
// Inspiration : LaTeXTrans (Summarizer), TransAgents.

import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import {
  SUMMARIZER_SYSTEM_PROMPT,
  buildSummarizerUserPrompt,
} from "../prompts/summarizer.system.js";
import { summarizerOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

export class SummarizerAgent extends Agent {
  readonly id = "summarizer";
  readonly name = "Resume";
  // stage "export" utilisé comme placeholder car le Summarizer est transverse
  // (pas dans la séquence WorkflowStage standard). Le WorkflowEngine l'appelle
  // directement via summarizeChapter().
  readonly stage = "export" as const;
  readonly outputSchema = summarizerOutputSchema;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
  ) {
    super();
  }

  /**
   * Produit un résumé de chapitre + met à jour le résumé du roman.
   * @param input.paragraphs  paragraphes source + traduits du chapitre
   * @param input.options.novelSummary  résumé précédent du roman (optionnel)
   * @returns metadata.chapterSummary + metadata.novelSummary
   */
  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const sourceText = paragraphs.map((p) => p.sourceText).join("\n\n");
    const translatedText = paragraphs
      .map((p) => p.translatedText ?? "")
      .join("\n\n");
    const novelSummary =
      (input.options?.novelSummary as string | undefined) ?? undefined;

    if (!sourceText.trim() && !translatedText.trim()) {
      logger.warn("[SummarizerAgent] Chapitre vide, résumé ignoré");
      return {
        metadata: {
          chapterSummary: "",
          novelSummary: novelSummary ?? "",
          skipped: true,
        },
      };
    }

    const userPrompt = buildSummarizerUserPrompt({
      sourceText,
      translatedText,
      novelSummary,
    });

    try {
      const response = await this.aiRouter.chat(
        this.config.providerId,
        [
          { role: "system", content: SUMMARIZER_SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        { jsonMode: true },
      );

      if (this.aiRouter.isEthicalRefusal(response)) {
        logger.warn("[SummarizerAgent] Refus éthique, résumé inchangé");
        return {
          metadata: {
            chapterSummary: "",
            novelSummary: novelSummary ?? "",
            ethicalRefusal: true,
          },
        };
      }

      const parsed = this.aiRouter.tryParseJson(response);
      if (parsed && typeof parsed === "object") {
        const obj = parsed as { chapterSummary?: unknown; novelSummary?: unknown };
        const chapterSummary =
          typeof obj.chapterSummary === "string" ? obj.chapterSummary : "";
        const updatedNovelSummary =
          typeof obj.novelSummary === "string" ? obj.novelSummary : novelSummary ?? "";
        return {
          metadata: { chapterSummary, novelSummary: updatedNovelSummary },
        };
      }

      logger.warn("[SummarizerAgent] Sortie LLM non parsable");
      return {
        metadata: {
          chapterSummary: "",
          novelSummary: novelSummary ?? "",
          parseError: true,
        },
      };
    } catch (err) {
      logger.warn("[SummarizerAgent] LLM summarize failed", {
        error: (err as Error).message,
      });
      return {
        metadata: {
          chapterSummary: "",
          novelSummary: novelSummary ?? "",
          error: (err as Error).message,
        },
      };
    }
  }
}

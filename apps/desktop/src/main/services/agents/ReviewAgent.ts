// v1 — 2026-07-08 (v1.4)
// Agent Review : analyse la traduction paragraphe-par-paragraphe et produit un
// ReviewReport (corrections ciblées). Inspiration honya (Reviewer), LaTeXTrans
// (Validator). C'est la passe qui distingue "traduction retry-boucle" de
// "traduction révisée comme par un humain".

import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  LexiconEntry,
  ReviewIssue,
  ReviewReport,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import {
  REVIEW_SYSTEM_PROMPT,
  buildReviewUserPrompt,
} from "../prompts/review.system.js";
import { reviewOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

export class ReviewAgent extends Agent {
  readonly id = "review";
  readonly name = "Réviseur";
  readonly stage = "review" as const;
  readonly outputSchema = reviewOutputSchema;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
  ) {
    super();
  }

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const sourceText = paragraphs.map((p) => p.sourceText).join("\n\n");
    const translatedText = paragraphs
      .map((p) => p.translatedText ?? "")
      .join("\n\n");
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";
    const novelSummary =
      (input.options?.novelSummary as string | undefined) ?? undefined;
    const lexicon = (input.lexicon ?? []).map((e: LexiconEntry) => ({
      term: e.term,
      translation: e.translation,
    }));

    const userPrompt = buildReviewUserPrompt({
      sourceText,
      translatedText,
      targetLanguage,
      novelSummary,
      lexicon,
    });

    const fallbackReport: ReviewReport = { issues: [], summary: "Review skipped (LLM unavailable)." };

    try {
      const response = await this.aiRouter.chat(
        this.config.providerId,
        [
          { role: "system", content: REVIEW_SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        { jsonMode: true },
      );

      // Détection de refus éthique
      if (this.aiRouter.isEthicalRefusal(response)) {
        logger.warn(
          "[ReviewAgent] Refus éthique détecté — rapport vide retourné",
        );
        return {
          report: { issues: [], summary: "Skipped: ethical refusal." },
          metadata: { ethicalRefusal: true },
        };
      }

      const parsed = this.aiRouter.tryParseJson(response);
      if (parsed && typeof parsed === "object" && Array.isArray((parsed as { issues?: unknown }).issues)) {
        const obj = parsed as { issues: unknown[]; summary?: unknown };
        const report: ReviewReport = {
          issues: obj.issues.map((raw) => this.normalizeIssue(raw)),
          summary: typeof obj.summary === "string" ? obj.summary : "",
        };
        // Score = pénalité basée sur le nombre d'issues high/medium
        const highCount = report.issues.filter((i) => i.severity === "high").length;
        const medCount = report.issues.filter((i) => i.severity === "medium").length;
        const penalty = Math.min(50, highCount * 10 + medCount * 4);
        const score = Math.max(40, 100 - penalty);
        return { report, score };
      }

      logger.warn("[ReviewAgent] Sortie LLM non parsable, rapport vide");
      return { report: fallbackReport, score: 90 };
    } catch (err) {
      logger.warn("[ReviewAgent] LLM review failed, returning empty report", {
        error: (err as Error).message,
      });
      return { report: fallbackReport, score: 90 };
    }
  }

  /** Normalise une issue brute (validité + bornage des champs) */
  private normalizeIssue(raw: unknown): ReviewIssue {
    const obj = raw as Record<string, unknown>;
    const severity = obj.severity === "high" || obj.severity === "medium" || obj.severity === "low"
      ? (obj.severity as ReviewIssue["severity"])
      : "medium";
    const validCategories = ["fidelity", "fluency", "terminology", "style", "consistency"] as const;
    const category = validCategories.includes(obj.category as (typeof validCategories)[number])
      ? (obj.category as ReviewIssue["category"])
      : "fidelity";
    return {
      paragraphIndex: typeof obj.paragraphIndex === "number" ? Math.max(0, Math.floor(obj.paragraphIndex)) : 0,
      severity,
      category,
      original: String(obj.original ?? ""),
      suggestion: String(obj.suggestion ?? ""),
      reason: String(obj.reason ?? ""),
    };
  }
}

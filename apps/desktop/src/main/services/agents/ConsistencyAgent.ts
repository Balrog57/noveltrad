import type { Agent, AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";
import type { ConsistencyChecker } from "../ConsistencyChecker.js";
import type { AiRouter } from "../AiRouter.js";
import type { ConsistencyReport } from "@shared/types/index.js";
import {
  CONSISTENCY_SYSTEM_PROMPT,
  buildConsistencyUserPrompt,
} from "../prompts/consistency.system.js";
import { logger } from "../../utils/logger.js";

export class ConsistencyAgent implements Agent {
  readonly id = "consistency";
  readonly name = "Cohérence";
  readonly stage = "consistency";

  constructor(
    private config: AgentConfig,
    private checker: ConsistencyChecker,
    private aiRouter: AiRouter,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const source = paragraphs.map((p) => p.sourceText);
    const target = paragraphs.map((p) => p.translatedText ?? "");
    const sourceText = source.join("\n\n");
    const translatedText = target.join("\n\n");

    // SDD §11.4 : construire la paire de langues pour appliquer les tolérances
    const sourceLang = input.options?.sourceLanguage as string | undefined;
    const targetLang = input.options?.targetLanguage as string | undefined;
    const languagePair =
      sourceLang && targetLang ? `${sourceLang}-${targetLang}` : undefined;

    // Phase 1 : LLM analysis
    let llmWarnings: Array<{
      severity: "low" | "medium" | "high";
      message: string;
    }> = [];
    let llmScore = 100;
    let llmAvailable = false;

    try {
      const lexiconBlock = this.buildLexiconBlock(input.lexicon);
      const userPrompt = buildConsistencyUserPrompt({
        sourceText,
        translatedText,
        lexiconBlock: lexiconBlock || undefined,
      });

      const response = await this.aiRouter.chat(
        this.config.providerId,
        [
          { role: "system", content: CONSISTENCY_SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        { jsonMode: true },
      );

      const parsed = this.aiRouter.tryParseJson(response);
      if (parsed && typeof parsed === "object") {
        const obj = parsed as Record<string, unknown>;
        if (Array.isArray(obj.warnings)) {
          llmWarnings = obj.warnings as Array<{
            severity: "low" | "medium" | "high";
            message: string;
          }>;
        }
        if (typeof obj.globalScore === "number") {
          llmScore = obj.globalScore;
        }
        llmAvailable = true;
      }
    } catch (err) {
      logger.warn(
        "[ConsistencyAgent] LLM analysis failed, using heuristics only",
        { error: (err as Error).message },
      );
    }

    // Phase 2 : Heuristic analysis (toujours exécutée)
    const heuristicReport = this.checker.check(
      source,
      target,
      input.lexicon ?? [],
      languagePair,
    );

    // Phase 3 : Merge LLM + heuristic
    const mergedWarnings = [...heuristicReport.warnings];
    if (llmAvailable) {
      for (const w of llmWarnings) {
        const isDuplicate = mergedWarnings.some(
          (hw) => hw.message === w.message,
        );
        if (!isDuplicate) {
          mergedWarnings.push(w);
        }
      }
    }

    const mergedScore = llmAvailable
      ? Math.round((heuristicReport.globalScore + llmScore) / 2)
      : heuristicReport.globalScore;

    return {
      report: {
        ...heuristicReport,
        warnings: mergedWarnings,
        globalScore: mergedScore,
      } as ConsistencyReport,
    };
  }

  private buildLexiconBlock(entries?: AgentInput["lexicon"]): string {
    if (!entries?.length) {return "";}
    const lines = entries.map(
      (e) =>
        `- ${e.term} → ${e.translation}${e.locked ? " (LOCKED)" : ""}`,
    );
    return `--- LEXICON ---\n${lines.join("\n")}\n--- END LEXICON ---\n\n`;
  }
}

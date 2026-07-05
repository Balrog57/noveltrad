import type { Agent, AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";
import type { LexiconEngine } from "../LexiconEngine.js";
import type { AiRouter } from "../AiRouter.js";
import {
  LEXICON_SYSTEM_PROMPT,
  buildLexiconUserPrompt,
} from "../prompts/lexicon.system.js";
import { logger } from "../../utils/logger.js";

export class LexiconAgent implements Agent {
  readonly id = "lexicon";
  readonly name = "Lexique";
  readonly stage = "lexicon";

  constructor(
    private config: AgentConfig,
    private lexiconEngine: LexiconEngine,
    private aiRouter: AiRouter,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    if (!input.projectId || !input.text) {return { text: input.text };}
    const text = input.text;
    const lexicon = input.lexicon ?? [];

    // Phase 1 : LLM suggestions
    let llmText: string | null = null;
    let llmSubstitutions: Array<{
      before: string;
      after: string;
      locked: boolean;
    }> = [];

    try {
      const lexiconBlock = this.buildLexiconBlock(lexicon);
      const userPrompt = buildLexiconUserPrompt({
        translatedText: text,
        lexiconBlock,
      });

      const response = await this.aiRouter.chat(
        this.config.providerId,
        [
          { role: "system", content: LEXICON_SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        { jsonMode: true },
      );

      const parsed = this.aiRouter.tryParseJson(response);
      if (parsed && typeof parsed === "object") {
        const obj = parsed as Record<string, unknown>;
        if (typeof obj.text === "string") {
          llmText = obj.text;
        }
        if (Array.isArray(obj.substitutions)) {
          llmSubstitutions = obj.substitutions as Array<{
            before: string;
            after: string;
            locked: boolean;
          }>;
        }
      }
    } catch (err) {
      logger.warn(
        "[LexiconAgent] LLM analysis failed, using lexicon engine only",
        { error: (err as Error).message },
      );
    }

    // Phase 2 : Lexicon engine (handles locked terms, forbidden, remaining)
    const engineInput = llmText ?? text;
    const engineResult = this.lexiconEngine.apply(engineInput, lexicon);

    // Phase 3 : Merge substitutions (LLM + engine, deduplicated)
    const mergedSubstitutions = [...llmSubstitutions];
    for (const sub of engineResult.substitutions) {
      const isDuplicate = mergedSubstitutions.some(
        (s) => s.before === sub.before && s.after === sub.after,
      );
      if (!isDuplicate) {
        mergedSubstitutions.push(sub);
      }
    }

    return {
      text: engineResult.text,
      substitutions: mergedSubstitutions,
    };
  }

  private buildLexiconBlock(entries: AgentInput["lexicon"]): string {
    if (!entries?.length) {return "";}
    const lines = entries.map(
      (e) =>
        `- ${e.term} → ${e.translation}${e.locked ? " (LOCKED)" : ""}`,
    );
    return `--- LEXICON ---\n${lines.join("\n")}\n--- END LEXICON ---\n\n`;
  }
}

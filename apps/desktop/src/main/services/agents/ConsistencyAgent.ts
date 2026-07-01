import type { Agent, AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";
import type { ConsistencyChecker } from "../ConsistencyChecker.js";

export class ConsistencyAgent implements Agent {
  readonly id = "consistency";
  readonly name = "Cohérence";
  readonly stage = "consistency";

  constructor(
    private config: AgentConfig,
    private checker: ConsistencyChecker,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const source = paragraphs.map((p) => p.sourceText);
    const target = paragraphs.map((p) => p.translatedText ?? "");

    // SDD §11.4 : construire la paire de langues pour appliquer les tolérances
    const sourceLang = input.options?.sourceLanguage as string | undefined;
    const targetLang = input.options?.targetLanguage as string | undefined;
    const languagePair =
      sourceLang && targetLang ? `${sourceLang}-${targetLang}` : undefined;

    const report = this.checker.check(
      source,
      target,
      input.lexicon ?? [],
      languagePair,
    );
    return { report };
  }
}

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
    const report = this.checker.check(source, target, input.lexicon ?? []);
    return { report };
  }
}

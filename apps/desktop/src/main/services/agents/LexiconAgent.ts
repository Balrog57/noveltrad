import type { Agent, AgentConfig } from "./Agent.js";
import type { AgentInput, AgentOutput } from "@shared/types/index.js";
import type { LexiconEngine } from "../LexiconEngine.js";

export class LexiconAgent implements Agent {
  readonly id = "lexicon";
  readonly name = "Lexique";
  readonly stage = "lexicon";

  constructor(
    private config: AgentConfig,
    private lexiconEngine: LexiconEngine,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    if (!input.projectId || !input.text) return { text: input.text };
    const result = this.lexiconEngine.apply(input.text, input.lexicon ?? []);
    return {
      text: result.text,
      substitutions: result.substitutions,
    };
  }
}

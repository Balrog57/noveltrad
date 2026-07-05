import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  Paragraph,
} from "@shared/types/index.js";
import { paragraphsOutputSchema } from "@shared/schemas/agent-io.js";

export class SplitAgent extends Agent {
  readonly id = "split";
  readonly name = "Découpage";
  readonly stage = "split";
  readonly outputSchema = paragraphsOutputSchema;

  constructor(private config: AgentConfig) {
    super();
  }

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? "";
    const paragraphs = text
      .split(/\n\n+/)
      .map((t) => t.trim())
      .filter(Boolean)
      .map((sourceText, index): Paragraph => ({
        id: crypto.randomUUID(),
        chapterId: input.chapterId ?? "",
        indexInChapter: index + 1,
        sourceText,
        translatedText: undefined,
        status: "pending",
      }));

    return { paragraphs };
  }
}

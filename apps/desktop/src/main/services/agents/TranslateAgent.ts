import type { Agent, AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  Paragraph,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import type { TranslationMemoryEngine } from "../TranslationMemoryEngine.js";

export class TranslateAgent implements Agent {
  readonly id = "translate";
  readonly name = "Traduction IA";
  readonly stage = "translate";

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
    private tmEngine: TranslationMemoryEngine,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const lexiconBlock = this.buildLexiconBlock(input.lexicon);
    const memoryBlock = this.buildMemoryBlock(input);

    const translated: Paragraph[] = [];
    for (const paragraph of paragraphs) {
      const prompt = `You are an expert literary translator. Translate the following ${input.options?.sourceLanguage ?? "text"} paragraph into ${input.options?.targetLanguage ?? "French"}.
${lexiconBlock}
${memoryBlock}
Source:
${paragraph.sourceText}

Output only the translated paragraph, nothing else.`;

      const response = await this.aiRouter.chat(this.config.providerId, [
        { role: "user", content: prompt },
      ]);

      translated.push({
        ...paragraph,
        translatedText: response.trim(),
        status: "translated",
      });
    }

    return { paragraphs: translated };
  }

  private buildLexiconBlock(entries?: AgentInput["lexicon"]): string {
    if (!entries?.length) return "";
    const lines = entries.map(
      (e) => `- ${e.term} → ${e.translation}${e.locked ? " (LOCKED)" : ""}`,
    );
    return `--- LEXICON ---\n${lines.join("\n")}\n--- END LEXICON ---\n`;
  }

  private buildMemoryBlock(input: AgentInput): string {
    if (!input.chapterId || !input.projectId) return "";
    const matches = this.tmEngine.fuzzyMatches(
      input.paragraphs?.[0]?.sourceText ?? "",
      input.projectId,
      3,
    );
    if (!matches.length) return "";
    const lines = matches.map((m) => `- "${m.sourceText}" → "${m.targetText}"`);
    return `--- TRANSLATION MEMORY ---\n${lines.join("\n")}\n--- END TM ---\n`;
  }
}

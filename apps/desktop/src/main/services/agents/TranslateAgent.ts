import type { Agent, AgentConfig } from "./Agent.js";
import type {
  AgentInput,
  AgentOutput,
  Paragraph,
  RagMatch,
} from "@shared/types/index.js";
import type { AiRouter } from "../AiRouter.js";
import type { TranslationMemoryEngine } from "../TranslationMemoryEngine.js";
import {
  TRANSLATE_SYSTEM_PROMPT,
  buildTranslateUserPrompt,
} from "../prompts/translate.system.js";

export class TranslateAgent implements Agent {
  readonly id = "translate";
  readonly name = "Traduction IA";
  readonly stage = "translate";

  private refusalDetected = false;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
    private tmEngine: TranslationMemoryEngine,
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? [];
    const lexiconBlock = this.buildLexiconBlock(input.lexicon);
    const memoryBlock = this.buildMemoryBlock(input);
    const sourceLanguage = (input.options?.sourceLanguage as string) ?? "text";
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";

    this.refusalDetected = false;
    const translated: Paragraph[] = [];

    // Lire le contexte RAG (paragraphes similaires déjà traduits)
    const ragContext = input.options?.ragContext as
      Record<string, RagMatch[]> | undefined;

    for (const paragraph of paragraphs) {
      const ragBlock = this.buildRagBlock(paragraph.id, ragContext);

      const userPrompt = buildTranslateUserPrompt({
        sourceText: paragraph.sourceText,
        sourceLanguage,
        targetLanguage,
        lexiconBlock,
        memoryBlock,
        ragBlock,
      });

      const response = await this.aiRouter.chat(this.config.providerId, [
        { role: "system", content: TRANSLATE_SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ]);

      // Détection de refus éthique
      if (this.aiRouter.isEthicalRefusal(response)) {
        this.refusalDetected = true;
        console.warn(
          `[TranslateAgent] Refus éthique détecté — conservation du texte source pour le paragraphe`,
        );
        translated.push({
          ...paragraph,
          translatedText: paragraph.sourceText,
          status: "pending",
        });
        continue;
      }

      translated.push({
        ...paragraph,
        translatedText: response.trim(),
        status: "translated",
      });
    }

    return {
      paragraphs: translated,
      metadata: this.refusalDetected ? { ethicalRefusal: true } : undefined,
    };
  }

  private buildLexiconBlock(entries?: AgentInput["lexicon"]): string {
    if (!entries?.length) return "";
    const lines = entries.map(
      (e) => `- ${e.term} → ${e.translation}${e.locked ? " (LOCKED)" : ""}`,
    );
    return `--- LEXICON ---\n${lines.join("\n")}\n--- END LEXICON ---\n\n`;
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
    return `--- TRANSLATION MEMORY ---\n${lines.join("\n")}\n--- END TM ---\n\n`;
  }

  /**
   * Construit le bloc RAG contenant les traductions similaires précédentes
   * pour servir d'exemples au modèle.
   */
  private buildRagBlock(
    paragraphId: string,
    ragContext?: Record<string, RagMatch[]>,
  ): string {
    if (!ragContext) return "";
    const matches = ragContext[paragraphId];
    if (!matches?.length) return "";

    const lines = matches.map(
      (m) => `Source: ${m.sourceText}\nTraduction: ${m.translatedText}`,
    );
    return `## Traductions similaires précédentes (pour référence) :\n${lines.join("\n\n")}\n\n`;
  }
}

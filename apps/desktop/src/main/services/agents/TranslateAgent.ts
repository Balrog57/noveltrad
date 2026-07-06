import { Agent } from "./Agent.js";
import type { AgentConfig } from "./Agent.js";
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
import { paragraphsOutputSchema } from "@shared/schemas/agent-io.js";
import { logger } from "../../utils/logger.js";

export class TranslateAgent extends Agent {
  readonly id = "translate";
  readonly name = "Traduction IA";
  readonly stage = "translate";
  readonly outputSchema = paragraphsOutputSchema;

  private refusalDetected = false;

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
    private tmEngine: TranslationMemoryEngine,
  ) {
    super();
  }

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
      // T11 : Vérifier d'abord la correspondance exacte TM
      if (input.projectId) {
        const tmExact = this.tmEngine.exactMatch(paragraph.sourceText, input.projectId);
        if (tmExact) {
          logger.info(
            `[TranslateAgent] Correspondance TM exacte trouvée pour le paragraphe ${paragraph.id}`,
          );
          translated.push({
            ...paragraph,
            translatedText: tmExact,
            status: "translated",
          });
          continue;
        }
      }

      const ragBlock = this.buildRagBlock(paragraph.id, ragContext);

      const userPrompt = buildTranslateUserPrompt({
        sourceText: paragraph.sourceText,
        sourceLanguage,
        targetLanguage,
        lexiconBlock,
        memoryBlock,
        ragBlock,
      });

      // T5 fix : résoudre le prompt via PromptLoader (override DB optionnel,
      // SDD §25). Si aucune version active n'existe en DB, la constante TS est
      // retournée (comportement inchangé).
      const systemPrompt = await this.aiRouter.resolvePrompt(
        "translate",
        TRANSLATE_SYSTEM_PROMPT,
      );

      const response = await this.aiRouter.chat(this.config.providerId, [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ]);

      // Détection de refus éthique
      if (this.aiRouter.isEthicalRefusal(response)) {
        this.refusalDetected = true;
        logger.warn(
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
    if (!entries?.length) {return "";}
    const lines = entries.map(
      (e) => `- ${e.term} → ${e.translation}${e.locked ? " (LOCKED)" : ""}`,
    );
    return `--- LEXICON ---\n${lines.join("\n")}\n--- END LEXICON ---\n\n`;
  }

  private buildMemoryBlock(input: AgentInput): string {
    if (!input.chapterId || !input.projectId) {return "";}
    const sourceText = input.paragraphs?.[0]?.sourceText ?? "";

    // T11 fix : utiliser la cascade findBestMatch 5 tiers (SDD §9.4) plutôt
    // que fuzzyMatches seul. La cascade tente dans l'ordre : project-exact,
    // project-fuzzy, global-exact, global-fuzzy. On complète ensuite avec des
    // matches fuzzy project pour atteindre jusqu'à 3 entrées de contexte.
    const matches: Array<{ sourceText: string; targetText: string; similarity: number }> = [];
    const seen = new Set<string>();

    const best = this.tmEngine.findBestMatch(sourceText, input.projectId);
    if (best) {
      matches.push({ sourceText: best.sourceText, targetText: best.targetText, similarity: best.similarity });
      seen.add(best.sourceText);
    }

    // Compléter avec fuzzy project (jusqu'à 3 entrées au total)
    const fuzzy = this.tmEngine.fuzzyMatches(sourceText, input.projectId, 3);
    for (const m of fuzzy) {
      if (matches.length >= 3) {break;}
      if (!seen.has(m.sourceText)) {
        matches.push({ sourceText: m.sourceText, targetText: m.targetText, similarity: m.similarity });
        seen.add(m.sourceText);
      }
    }

    if (!matches.length) {return "";}
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
    if (!ragContext) {return "";}
    const matches = ragContext[paragraphId];
    if (!matches?.length) {return "";}

    const lines = matches.map(
      (m) => `Source: ${m.sourceText}\nTraduction: ${m.translatedText}`,
    );
    return `## Traductions similaires précédentes (pour référence) :\n${lines.join("\n\n")}\n\n`;
  }
}

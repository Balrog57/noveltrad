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
    // Pré-scan glossary : ne pas envoyer tout le lexique du projet (potentiellement
    // des centaines d'entrées) au LLM. On ne garde que les termes (et alias)
    // réellement présents dans le texte source du chapitre, plus tous les termes
    // verrouillés (peu nombreux et critiques pour la cohérence).
    const chapterSourceText = paragraphs.map((p) => p.sourceText).join("\n");
    const filteredLexicon = this.filterLexiconForChapter(input.lexicon, chapterSourceText);
    const lexiconBlock = this.buildLexiconBlock(filteredLexicon);
    const memoryBlock = this.buildMemoryBlock(input);
    const sourceLanguage = (input.options?.sourceLanguage as string) ?? "text";
    const targetLanguage =
      (input.options?.targetLanguage as string) ?? "French";

    this.refusalDetected = false;
    let lengthAnomalyCount = 0;
    const translated: Paragraph[] = [];

    // Lire le contexte RAG (paragraphes similaires déjà traduits)
    const ragContext = input.options?.ragContext as
      Record<string, RagMatch[]> | undefined;

    /**
     * Garde-fou anti-résumé : un traducteur littéraire ne doit jamais résumer.
     * Si la traduction fait < 90% du nombre de mots source (et que le source
     * est assez long pour éviter les faux positifs), on marque le paragraphe
     * `pending` pour que le reviewer/QA le voie, et on lève un flag metadata.
     */
    const isLengthAnomaly = (source: string, translatedText: string): boolean => {
      const sourceWords = source.split(/\s+/).filter(Boolean).length;
      if (sourceWords < 20) {return false;} // phrases courtes : bruit
      const translatedWords = translatedText.split(/\s+/).filter(Boolean).length;
      return translatedWords < sourceWords * 0.9;
    };

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

      // Garde-fou anti-résumé : si la sortie est < 90% des mots source, le
      // modèle a probablement résumé ou omis du contenu. On garde la traduction
      // (pour review) mais on marque le paragraphe pending + flag metadata.
      const trimmedResponse = response.trim();
      const anomaly = isLengthAnomaly(paragraph.sourceText, trimmedResponse);
      if (anomaly) {
        lengthAnomalyCount += 1;
        logger.warn(
          `[TranslateAgent] Anomalie de longueur détectée (résumé possible) pour le paragraphe ${paragraph.id}`,
        );
      }

      translated.push({
        ...paragraph,
        translatedText: trimmedResponse,
        status: anomaly ? "pending" : "translated",
      });
    }

    const metadata: Record<string, unknown> = {};
    if (this.refusalDetected) {metadata.ethicalRefusal = true;}
    if (lengthAnomalyCount > 0) {metadata.lengthAnomaly = true; metadata.anomalyCount = lengthAnomalyCount;}

    return {
      paragraphs: translated,
      metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
    };
  }

  /**
   * Pré-scan glossary : filtre le lexique pour ne garder que les entrées
   * pertinentes au chapitre courant.
   *
   * Règles :
   * - Une entrée est retenue si son `term` ou l'un de ses `aliases` apparaît
   *   dans le texte source (recherche sous-chaîne, fonctionne aussi pour les
   *   langues sans espaces comme le chinois).
   * - Les entrées `locked` sont TOUJOURS retenues : elles sont peu nombreuses
   *   et critiques pour la cohérence (noms propres, terminologie imposée).
   *
   * Économie typique : on passe de plusieurs centaines d'entrées à 5-15 termes
   * utiles, ce qui réduit fortement les tokens du prompt de traduction.
   */
  private filterLexiconForChapter(
    entries: AgentInput["lexicon"],
    chapterSourceText: string,
  ): AgentInput["lexicon"] {
    if (!entries?.length || chapterSourceText.length === 0) {return entries;}
    return entries.filter((e) => {
      if (e.locked) {return true;}
      if (chapterSourceText.includes(e.term)) {return true;}
      return (e.aliases ?? []).some((alias) => chapterSourceText.includes(alias));
    });
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

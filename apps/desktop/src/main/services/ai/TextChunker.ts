import type { ChatMessage } from "@shared/types/index.js";
import { logger } from "../../utils/logger.js";

/**
 * WS-3 (clean architecture) : extrait de AiRouter.chatWithChunking +
 * loadTokenizer.
 *
 * SDD §3.6b : Chat avec découpage automatique si le prompt dépasse 50% de la
 * fenêtre contextuelle du modèle.
 *
 * Le chunker ne fait PAS d'appels LLM lui-même — il découpe les messages et
 * appelle une fonction `chat` fournie par l'appelant (AiRouter). Cela permet
 * de tester la logique de découpage indépendamment du provider.
 */
export type ChatFn = (
  messages: ChatMessage[],
) => Promise<{ content: string }>;

export class TextChunker {
  /**
   * Découpe le texte utilisateur en chunks si le prompt total dépasse 50%
   * de la context window. Appelle `chat` par chunk (bénéficie du cache
   * AiCache côté AiRouter), réassemble les résultats.
   *
   * Si en dessous du seuil, appelle `chat` une seule fois sans découpage.
   *
   * @param messages      Messages complets (system + user).
   * @param chat          Fonction de chat fournie par AiRouter (1 chunk = 1 appel).
   * @param contextWindow Taille de la fenêtre contextuelle (défaut 32768).
   */
  async chunk(
    messages: ChatMessage[],
    chat: ChatFn,
    contextWindow: number = 32768,
  ): Promise<string> {
    const encode = await this.loadTokenizer();

    const fullText = messages.map((m) => m.content).join("\n");
    const totalTokens = encode(fullText).length;

    // Si en dessous du seuil, pas de découpage nécessaire
    if (totalTokens <= contextWindow * 0.5) {
      const r = await chat(messages);
      return r.content;
    }

    // Séparer les messages système (gardés avec chaque chunk)
    const systemMessages = messages.filter((m) => m.role === "system");
    const userTexts = messages
      .filter((m) => m.role === "user")
      .map((m) => m.content)
      .join("\n\n");

    // Découper le texte utilisateur en paragraphes
    const paragraphs = userTexts.split(/\n\n+/).filter((p) => p.trim().length > 0);
    if (paragraphs.length === 0) {
      const r = await chat(messages);
      return r.content;
    }

    const systemTokens = systemMessages.length > 0
      ? encode(systemMessages.map((m) => m.content).join("\n")).length
      : 0;
    const chunkThreshold = Math.floor(contextWindow * 0.45);

    const chunks: string[] = [];
    let currentBatch: string[] = [];
    let currentTokens = 0;

    for (const para of paragraphs) {
      const paraTokens = encode(para).length;

      if (
        currentTokens + paraTokens + systemTokens > chunkThreshold &&
        currentBatch.length > 0
      ) {
        const chunkText = currentBatch.join("\n\n");
        // SDD §3.8 : chaque chunk passe par chat() (cache + accumulateur usage).
        const chunkResult = await chat([
          ...systemMessages,
          { role: "user", content: chunkText },
        ]);
        chunks.push(chunkResult.content);

        currentBatch = [para];
        currentTokens = paraTokens;
      } else {
        currentBatch.push(para);
        currentTokens += paraTokens;
      }
    }

    if (currentBatch.length > 0) {
      const chunkText = currentBatch.join("\n\n");
      const chunkResult = await chat([
        ...systemMessages,
        { role: "user", content: chunkText },
      ]);
      chunks.push(chunkResult.content);
    }

    return chunks.join("\n\n");
  }

  /**
   * Charge paresseusement gpt-tokenizer (import ESM peut échouer en production asar).
   * Fallback : estimation 1 token ≈ 4 caractères.
   */
  private async loadTokenizer(): Promise<(text: string) => { length: number }> {
    try {
      const { encode: gptEncode } = await import("gpt-tokenizer");
      return gptEncode;
    } catch {
      logger.warn("[AiRouter] gpt-tokenizer indisponible, fallback estimation");
      return (text: string) => ({
        length: Math.ceil(text.length / 4),
      });
    }
  }
}

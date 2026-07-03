import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
} from "@shared/types/index.js";
import type { AiCache } from "./AiCache.js";
import { logger } from "../utils/logger.js";
import { encode as gptEncode } from "gpt-tokenizer";

export class AiRouter {
  private providers: Map<string, AiProvider> = new Map();
  private aiCache?: AiCache;
  /** SDD §15 : callback pour obtenir un provider depuis un plugin */
  private getPluginProviderFn?: (id: string) => AiProvider | undefined;

  register(provider: AiProvider): void {
    this.providers.set(provider.id, provider);
  }

  /** SDD §15 : enregistre une fonction pour résoudre les providers via PluginHost */
  setPluginProviderResolver(fn: (id: string) => AiProvider | undefined): void {
    this.getPluginProviderFn = fn;
  }

  /** Active le cache des réponses IA (SDD §22.1) */
  setCache(cache: AiCache): void {
    this.aiCache = cache;
  }

  get(id: string): AiProvider {
    // SDD §15 : vérifier d'abord les providers built-in
    const provider = this.providers.get(id);
    if (provider) return provider;
    // SDD §15 : puis vérifier les plugins
    if (this.getPluginProviderFn) {
      const pluginProvider = this.getPluginProviderFn(id);
      if (pluginProvider) return pluginProvider;
    }
    throw new Error(`Provider inconnu : ${id}`);
  }

  async chat(
    providerId: string,
    messages: ChatMessage[],
    options?: ChatOptions,
  ): Promise<string> {
    const provider = this.get(providerId);

    // SDD §22.1 : vérifier le cache avant d'appeler le LLM
    if (this.aiCache) {
      const systemPrompt = messages
        .filter((m) => m.role === "system")
        .map((m) => m.content)
        .join("\n");
      const userPrompt = messages
        .filter((m) => m.role === "user")
        .map((m) => m.content)
        .join("\n");
      const temperature = options?.temperature ?? 0.7;
      const cacheKey = this.aiCache.generateKey(
        systemPrompt,
        userPrompt,
        provider.model ?? "unknown",
        temperature,
      );
      const cached = this.aiCache.get(cacheKey);
      if (cached !== null) {
        return cached;
      }

      const response = await provider.chat(messages, options);

      // Stocker la réponse dans le cache pour les appels futurs
      this.aiCache.set(cacheKey, response);
      return response;
    }

    return provider.chat(messages, options);
  }

  async *streamChat(
    providerId: string,
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string> {
    yield* this.get(providerId).streamChat(messages, options);
  }

  /**
   * SDD §3.6b : Chat avec découpage automatique si le prompt dépasse 50%
   * de la fenêtre contextuelle du modèle.
   *
   * 1. Estime les tokens du prompt via gpt-tokenizer
   * 2. Si > 50% context window → découpe le texte utilisateur en chunks par
   *    paragraphes (chaque chunk garde les messages système)
   * 3. Appelle `chat()` par chunk (bénéficie du cache AiCache)
   * 4. Réassemble les résultats
   *
   * @param contextWindow Taille de la fenêtre contextuelle du modèle (défaut 32768)
   */
  async chatWithChunking(
    providerId: string,
    messages: ChatMessage[],
    options?: ChatOptions,
    contextWindow: number = 32768,
  ): Promise<string> {
    const fullText = messages.map((m) => m.content).join("\n");
    const totalTokens = gptEncode(fullText).length;

    // Si en dessous du seuil, pas de découpage nécessaire
    if (totalTokens <= contextWindow * 0.5) {
      return this.chat(providerId, messages, options);
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
      // Aucun contenu utilisateur, fallback au chat normal
      return this.chat(providerId, messages, options);
    }

    const systemTokens = systemMessages.length > 0
      ? gptEncode(systemMessages.map((m) => m.content).join("\n")).length
      : 0;
    // Seuil par chunk : 45% de la fenêtre (marge pour la réponse)
    const chunkThreshold = Math.floor(contextWindow * 0.45);

    const chunks: string[] = [];
    let currentBatch: string[] = [];
    let currentTokens = 0;

    for (const para of paragraphs) {
      const paraTokens = gptEncode(para).length;

      // Si un paragraphe seul dépasse le seuil, on le force dans un chunk seul
      // (le LLM fera au mieux avec ce qu'il reçoit)
      if (
        currentTokens + paraTokens + systemTokens > chunkThreshold &&
        currentBatch.length > 0
      ) {
        // Finaliser le chunk en cours
        const chunkText = currentBatch.join("\n\n");
        const chunkResult = await this.chat(providerId, [
          ...systemMessages,
          { role: "user", content: chunkText },
        ], options);
        chunks.push(chunkResult);

        currentBatch = [para];
        currentTokens = paraTokens;
      } else {
        currentBatch.push(para);
        currentTokens += paraTokens;
      }
    }

    // Dernier chunk
    if (currentBatch.length > 0) {
      const chunkText = currentBatch.join("\n\n");
      const chunkResult = await this.chat(providerId, [
        ...systemMessages,
        { role: "user", content: chunkText },
      ], options);
      chunks.push(chunkResult);
    }

    return chunks.join("\n\n");
  }

  /**
   * Tente de parser une chaîne brute en JSON avec plusieurs stratégies de fallback.
   * 1. JSON.parse() direct
   * 2. Extraction depuis des fences markdown ```json ... ```
   * 3. Réparation basique (trailing commas, single quotes)
   * Retourne null si toutes les stratégies échouent.
   */
  tryParseJson(raw: string): unknown {
    // 1. Essai direct
    try {
      return JSON.parse(raw);
    } catch {
      // continue
    }

    // 2. Extraction depuis des fences markdown ```json ... ```
    const fenceMatch = raw.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
    if (fenceMatch) {
      try {
        return JSON.parse(fenceMatch[1].trim());
      } catch {
        // continue
      }
    }

    // 3. Réparation basique des erreurs JSON courantes
    try {
      let fixed = raw.trim();
      // Supprimer les trailing commas avant } ou ]
      fixed = fixed.replace(/,(\s*[}\]])/g, "$1");
      // Remplacer les single quotes par des double quotes (approche simple)
      // Note : ne gère pas les apostrophes à l'intérieur des chaînes
      fixed = fixed.replace(/'/g, '"');
      const result = JSON.parse(fixed);
      logger.warn(
        "[AiRouter] JSON réparé (fallback single quotes / trailing commas)",
      );
      return result;
    } catch {
      // continue
    }

    return null;
  }

  /**
   * Détecte si le texte est un refus éthique du LLM
   * (refus de traduction, contenu inapproprié, etc.)
   */
  isEthicalRefusal(text: string): boolean {
    const trimmed = text.trim();
    const refusalPatterns = [
      /^I cannot/i,
      /^I('|’)m sorry/i,
      /^I apologize/i,
      /^As an AI/i,
      /^抱歉/,
      /^无法/,
      /^我不能/,
    ];
    return refusalPatterns.some((pattern) => pattern.test(trimmed));
  }
}

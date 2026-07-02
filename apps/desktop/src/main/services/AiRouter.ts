import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
} from "@shared/types/index.js";
import type { AiCache } from "./AiCache.js";
import { logger } from "../utils/logger.js";

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
      const prompt = messages.map((m) => m.content).join("\n");
      const temperature = options?.temperature ?? 0.7;
      const cacheKey = this.aiCache.generateKey(
        prompt,
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

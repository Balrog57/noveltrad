import pRetry, { AbortError } from "p-retry";
import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
} from "@shared/types/index.js";
import type { AiCache } from "./AiCache.js";
import type { PromptLoader } from "./prompts/PromptLoader.js";
import { logger } from "../utils/logger.js";

export class AiRouter {
  private providers: Map<string, AiProvider> = new Map();
  private aiCache?: AiCache;
  private promptLoader?: PromptLoader;
  /** SDD §15 : callback pour obtenir un provider depuis un plugin */
  private getPluginProviderFn?: (id: string) => AiProvider | undefined;
  /** SDD §3.8 : coûts par modèle (clé = model id). Vide = pas de suivi. */
  private modelCosts: Record<string, { costPerInputToken: number; costPerOutputToken: number }> = {};

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

  /** SDD §3.8 : configure les coûts par modèle (lus depuis les settings) */
  setModelCosts(costs: Record<string, { costPerInputToken: number; costPerOutputToken: number }>): void {
    this.modelCosts = costs ?? {};
  }

  /**
   * SDD §3.8 : estime le coût USD d'un appel.
   * @returns 0 si le modèle n'est pas configuré (local/gratuit) ou si pas de tokens.
   */
  estimateCost(modelId: string, inputTokens: number, outputTokens: number): number {
    const cost = this.modelCosts[modelId];
    if (!cost) {return 0;}
    return (
      (inputTokens / 1000) * cost.costPerInputToken +
      (outputTokens / 1000) * cost.costPerOutputToken
    );
  }

  /**
   * Enregistre un PromptLoader pour la résolution de prompts avec override DB
   * (SDD §25 — Prompt Book). Méthode additive : les agents continuent d'utiliser
   * leurs imports directs ; le loader offre une capacité d'override runtime.
   */
  setPromptLoader(loader: PromptLoader): void {
    this.promptLoader = loader;
  }

  /**
   * T5 fix : résout un prompt avec override DB optionnel.
   *
   * Les agents appellent cette méthode avec leur identifiant de prompt et la
   * constante TS par défaut. Si un PromptLoader est enregistré et qu'une
   * version active existe en DB, elle remplace la constante. Sinon, la
   * constante TS est retournée (comportement inchangé).
   *
   * Usage côté agent :
   *   const prompt = await this.aiRouter.resolvePrompt("translate", TRANSLATE_SYSTEM_PROMPT);
   *
   * @param promptId Identifiant du prompt (ex "translate", "qa", "consistency")
   * @param defaultContent Constante TS de fallback
   */
  async resolvePrompt(promptId: string, defaultContent: string): Promise<string> {
    if (!this.promptLoader) {
      return defaultContent;
    }
    try {
      return await this.promptLoader.load(promptId);
    } catch {
      // Prompt inconnu du loader → fallback constant TS
      return defaultContent;
    }
  }

  get(id: string): AiProvider {
    // SDD §15 : vérifier d'abord les providers built-in
    const provider = this.providers.get(id);
    if (provider) {return provider;}
    // SDD §15 : puis vérifier les plugins
    if (this.getPluginProviderFn) {
      const pluginProvider = this.getPluginProviderFn(id);
      if (pluginProvider) {return pluginProvider;}
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

      // SDD §7.10 : Retry réseau (5xx, ECONNREFUSED, timeout), pas de retry sur 4xx
      const response = await pRetry(
        () => provider.chat(messages, options),
        {
          retries: 3,
          factor: 2,
          minTimeout: 1000,
          onFailedAttempt: (err) => {
            logger.warn(
              `[AiRouter] chat() tentative ${err.attemptNumber} échouée (${err.retriesLeft} restantes)`,
              { error: err.error?.message },
            );
          },
        },
      );

      // Stocker la réponse dans le cache pour les appels futurs
      this.aiCache.set(cacheKey, response);
      return response;
    }

    // SDD §7.10 : Retry réseau (5xx, ECONNREFUSED, timeout), pas de retry sur 4xx
    return pRetry(
      () => provider.chat(messages, options),
      {
        retries: 3,
        factor: 2,
        minTimeout: 1000,
        onFailedAttempt: (err) => {
          logger.warn(
            `[AiRouter] chat() tentative ${err.attemptNumber} échouée (${err.retriesLeft} restantes)`,
            { error: err.error?.message },
          );
        },
      },
    );
  }

  async *streamChat(
    providerId: string,
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string> {
    // SDD §7.10 : Retry réseau sur l'établissement de la connexion stream
    const provider = this.get(providerId);
    const stream = await pRetry(
      () => provider.streamChat(messages, options),
      {
        retries: 3,
        factor: 2,
        minTimeout: 1000,
        onFailedAttempt: (err) => {
          logger.warn(
            `[AiRouter] streamChat() tentative ${err.attemptNumber} échouée (${err.retriesLeft} restantes)`,
            { error: err.error?.message },
          );
        },
      },
    );
    yield* stream;
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
    const encode = await this.loadTokenizer();

    const fullText = messages.map((m) => m.content).join("\n");
    const totalTokens = encode(fullText).length;

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
      return this.chat(providerId, messages, options);
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

  /** Charge paresseusement gpt-tokenizer (import ESM peut échouer en production asar).
   *  Fallback : estimation 1 token ≈ 4 caractères. */
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

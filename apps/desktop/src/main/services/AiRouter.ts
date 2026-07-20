import pRetry from "p-retry";
import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
  TokenUsage,
} from "@shared/types/index.js";
import type { AiCache } from "./AiCache.js";
import type { PromptLoader } from "./prompts/PromptLoader.js";
import { logger } from "../utils/logger.js";
// WS-3 (clean architecture) : collaborateurs extraits du god-class.
import { TokenUsageAccumulator } from "./ai/TokenUsageAccumulator.js";
import { CostEstimator, type ModelCost } from "./ai/CostEstimator.js";
import { TextChunker } from "./ai/TextChunker.js";
import { PromptResolver } from "./ai/PromptResolver.js";
import { tryParseJson } from "./ai/jsonRepair.js";
import { isEthicalRefusal } from "./ai/refusalDetector.js";

/**
 * AiRouter — facade de routage vers les providers IA.
 *
 * WS-3 (clean architecture) : la classe original mélangeait 8
 * responsabilités (routing, coûts, usage tokens, chunking, JSON repair,
 * détection refus, résolution prompts, retry réseau). Elle est désormais
 * une FACADE qui délègue aux collaborateurs `services/ai/*` :
 *   - {@link TokenUsageAccumulator} : accumulateur d'usage step
 *   - {@link CostEstimator}         : coûts par modèle
 *   - {@link TextChunker}           : découpage longs chapitres
 *   - {@link PromptResolver}        : override DB des prompts
 *   - {@link tryParseJson}          : (pure fn) repair JSON
 *   - {@link isEthicalRefusal}      : (pure fn) détection refus
 *
 * L'API publique est **inchangée** (byte-compatible) — les 16 call-sites
 * agents et le WorkflowEngine n'ont pas besoin de modification. Le routing
 * (registry + get/register + chat/stream + retry réseau) reste ici car c'est
 * le cœur du rôle de "router" et il coordonne plusieurs collaborators
 * (cache, accumulateur, providers).
 */
export class AiRouter {
  private providers: Map<string, AiProvider> = new Map();
  private aiCache?: AiCache;
  /** SDD §15 : callback pour obtenir un provider depuis un plugin */
  private getPluginProviderFn?: (id: string) => AiProvider | undefined;

  private readonly usage = new TokenUsageAccumulator();
  private readonly costs = new CostEstimator();
  private readonly chunker = new TextChunker();
  private readonly prompts = new PromptResolver();

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
  setModelCosts(costs: Record<string, ModelCost>): void {
    this.costs.setModelCosts(costs);
  }

  /**
   * SDD §3.8 : estime le coût USD d'un appel.
   * @returns 0 si le modèle n'est pas configuré (local/gratuit) ou si pas de tokens.
   */
  estimateCost(modelId: string, inputTokens: number, outputTokens: number): number {
    return this.costs.estimateCost(modelId, inputTokens, outputTokens);
  }

  /** SDD §3.8 : réinitialise l'accumulateur d'usage de tokens (début de step). */
  resetUsage(): void {
    this.usage.reset();
  }

  /**
   * SDD §3.8 : retourne l'usage accumulé depuis le dernier resetUsage() et
   * le réinitialise. Retourne undefined si aucun appel n'a été fait.
   */
  getAndResetUsage(): TokenUsage | undefined {
    return this.usage.getAndReset();
  }

  /**
   * Enregistre un PromptLoader pour la résolution de prompts avec override DB
   * (SDD §25 — Prompt Book). Méthode additive : les agents continuent d'utiliser
   * leurs imports directs ; le loader offre une capacité d'override runtime.
   */
  setPromptLoader(loader: PromptLoader): void {
    this.prompts.setLoader(loader);
  }

  /**
   * T5 fix : résout un prompt avec override DB optionnel.
   *
   * Les agents appellent cette méthode avec leur identifiant de prompt et la
   * constante TS par défaut. Si un PromptLoader est enregistré et qu'une
   * version active existe en DB, elle remplace la constante. Sinon, la
   * constante TS est retournée (comportement inchangé).
   */
  async resolvePrompt(promptId: string, defaultContent: string): Promise<string> {
    return this.prompts.resolve(promptId, defaultContent);
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
    const result = await this.chatWithUsage(providerId, messages, options);
    return result.content;
  }

  /**
   * SDD §3.8 : variante de chat() qui retourne aussi l'usage de tokens.
   * Utilisée par l'AiRouter pour accumuler l'usage (accumulateur interne) et
   * par le WorkflowEngine pour remplir step.tokensIn/Out.
   *
   * Délègue à `provider.chatWithUsage()` si le provider l'implémente (capture
   * l'usage), sinon fallback à `provider.chat()` (usage undefined).
   */
  async chatWithUsage(
    providerId: string,
    messages: ChatMessage[],
    options?: ChatOptions,
  ): Promise<{ content: string; usage?: TokenUsage }> {
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
        // HIT cache : pas d'appel provider, pas d'usage à accumuler.
        return { content: cached };
      }

      const result = await this.callProviderWithUsage(provider, messages, options);
      this.usage.add(result.usage);
      this.aiCache.set(cacheKey, result.content);
      return result;
    }

    const result = await this.callProviderWithUsage(provider, messages, options);
    this.usage.add(result.usage);
    return result;
  }

  /**
   * @internal : effectue l'appel provider avec retry réseau, en utilisant
   * chatWithUsage() si disponible (capture usage), sinon chat() (usage = undefined).
   */
  private async callProviderWithUsage(
    provider: AiProvider,
    messages: ChatMessage[],
    options?: ChatOptions,
  ): Promise<{ content: string; usage?: TokenUsage }> {
    return pRetry(
      async () => {
        if (provider.chatWithUsage) {
          return provider.chatWithUsage(messages, options);
        }
        const content = await provider.chat(messages, options);
        return { content };
      },
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
   * Délègue au collaborateur {@link TextChunker} en lui passant une fonction
   * `chat` qui appelle `chatWithUsage` (bénéficie du cache AiCache et accumule
   * l'usage de chaque chunk).
   *
   * @param contextWindow Taille de la fenêtre contextuelle du modèle (défaut 32768)
   */
  async chatWithChunking(
    providerId: string,
    messages: ChatMessage[],
    options?: ChatOptions,
    contextWindow: number = 32768,
  ): Promise<string> {
    return this.chunker.chunk(
      messages,
      (msgs) => this.chatWithUsage(providerId, msgs, options),
      contextWindow,
    );
  }

  /**
   * Tente de parser une chaîne brute en JSON avec plusieurs stratégies de fallback.
   * @see {tryParseJson} (pure fn dans services/ai/jsonRepair.ts)
   */
  tryParseJson(raw: string): unknown {
    return tryParseJson(raw);
  }

  /**
   * Détecte si le texte est un refus éthique du LLM.
   * @see {isEthicalRefusal} (pure fn dans services/ai/refusalDetector.ts)
   */
  isEthicalRefusal(text: string): boolean {
    return isEthicalRefusal(text);
  }
}

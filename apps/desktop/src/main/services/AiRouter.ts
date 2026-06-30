import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
} from "@shared/types/index.js";

export class AiRouter {
  private providers: Map<string, AiProvider> = new Map();

  register(provider: AiProvider): void {
    this.providers.set(provider.id, provider);
  }

  get(id: string): AiProvider {
    const provider = this.providers.get(id);
    if (!provider) throw new Error(`Provider inconnu : ${id}`);
    return provider;
  }

  async chat(
    providerId: string,
    messages: ChatMessage[],
    options?: ChatOptions,
  ): Promise<string> {
    return this.get(providerId).chat(messages, options);
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
      console.warn(
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

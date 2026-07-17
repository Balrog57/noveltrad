import OpenAI from "openai";
import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
  ChatResult,
  TokenUsage,
} from "@shared/types/index.js";
import { sleepForRetryAfter, retryable429Error } from "./retry.js";

/**
 * SDD §3.7 : Gestion réactive du HTTP 429 pour les providers cloud.
 *
 * Le SDK OpenAI lance APIError avec .status. En cas de 429, on respecte
 * l'en-tête Retry-After (via err.headers), on attend, puis on relance une
 * Error retryable (pas AbortError) pour que le pRetry de l'AiRouter retraite.
 *
 * P2-7 refactor : le sleep + log est délégué à sleepForRetryAfter (shared).
 */
async function handle429IfApplicable(err: unknown): Promise<void> {
  if (!(err instanceof OpenAI.APIError)) {return;}
  if (err.status !== 429) {return;}
  // err.headers est un objet Headers-like
  const headers = err.headers as Record<string, string> | undefined;
  const retryAfter = headers?.["retry-after"] ?? headers?.["Retry-After"];
  await sleepForRetryAfter(retryAfter, "[OpenAiCompatible]");
  // Rethrow comme Error simple (retryable par pRetry)
  throw retryable429Error();
}

export class OpenAiCompatibleProvider implements AiProvider {
  private client: OpenAI;

  constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly model: string,
    public readonly baseURL: string,
    public readonly apiKey?: string,
  ) {
    this.client = new OpenAI({ baseURL, apiKey });
  }

  async listModels(): Promise<string[]> {
    const response = await this.client.models.list();
    return response.data.map((m) => m.id);
  }

  async chat(messages: ChatMessage[], options?: ChatOptions): Promise<string> {
    const result = await this.chatWithUsage(messages, options);
    return result.content;
  }

  /**
   * SDD §3.8 : variante de chat() qui capture l'objet `usage` renvoyé par
   * l'API OpenAI (prompt_tokens / completion_tokens / total_tokens).
   * Permet le suivi de consommation pour la facturation et le cap maxJobTokens.
   */
  async chatWithUsage(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): Promise<ChatResult> {
    try {
      const response = await this.client.chat.completions.create({
        model: this.model,
        messages,
        temperature: options?.temperature ?? 0.7,
        response_format: options?.jsonMode ? { type: "json_object" } : undefined,
      });
      const content = response.choices[0]?.message?.content ?? "";
      // SDD §3.8 : extraire l'usage si le provider le renvoie (cloud uniquement)
      let usage: TokenUsage | undefined;
      const rawUsage = response.usage as
        | { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number }
        | undefined;
      if (rawUsage && typeof rawUsage.total_tokens === "number") {
        usage = {
          promptTokens: rawUsage.prompt_tokens ?? 0,
          completionTokens: rawUsage.completion_tokens ?? 0,
          totalTokens: rawUsage.total_tokens,
        };
      }
      return { content, usage };
    } catch (err) {
      await handle429IfApplicable(err);
      throw err;
    }
  }

  async *streamChat(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string> {
    // SDD §7.10 : le retry de connexion est géré par AiRouter. Ici on gère
    // uniquement le 429 sur l'établissement du stream.
    let stream: Awaited<ReturnType<typeof this.client.chat.completions.create>>;
    try {
      stream = await this.client.chat.completions.create({
        model: this.model,
        messages,
        temperature: options?.temperature ?? 0.7,
        stream: true,
        response_format: options?.jsonMode ? { type: "json_object" } : undefined,
      });
    } catch (err) {
      await handle429IfApplicable(err);
      throw err;
    }
    for await (const chunk of stream) {
      yield chunk.choices[0]?.delta?.content ?? "";
    }
  }

  async embeddings(texts: string[]): Promise<number[][]> {
    try {
      const response = await this.client.embeddings.create({
        model: this.model,
        input: texts,
      });
      return response.data.map((d) => d.embedding);
    } catch (err) {
      await handle429IfApplicable(err);
      throw err;
    }
  }

  async isAvailable(): Promise<boolean> {
    try {
      await this.listModels();
      return true;
    } catch {
      return false;
    }
  }
}

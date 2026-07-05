import { net } from "electron";
import pRetry, { AbortError } from "p-retry";
import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
} from "@shared/types/index.js";
import { logger } from "../../utils/logger.js";

export class OllamaProvider implements AiProvider {
  constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly model: string,
    public readonly host: string = "http://localhost:11434",
  ) {}

  async listModels(): Promise<string[]> {
    const res = await net.fetch(`${this.host}/api/tags`, { signal: AbortSignal.timeout(10_000) });
    if (!res.ok) {throw new Error(`HTTP ${res.status}`);}
    const data = await res.json();
    return data.models.map((m: { name: string }) => m.name);
  }

  async chat(messages: ChatMessage[], options?: ChatOptions): Promise<string> {
    return pRetry(
      async () => {
        const res = await net.fetch(`${this.host}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: this.model,
            messages,
            stream: false,
            options: {
              temperature: options?.temperature ?? 0.7,
              num_predict: options?.maxTokens,
            },
            format: options?.jsonMode ? "json" : undefined,
          }),
          signal: AbortSignal.timeout(300_000),
        });
        if (!res.ok) {
          if (res.status >= 400 && res.status < 500) {
            throw new AbortError(`HTTP ${res.status}`);
          }
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        return data.message.content;
      },
      {
        retries: 3,
        factor: 2,
        minTimeout: 1000,
        onFailedAttempt: (err) => {
          logger.warn(
            `[OllamaProvider] chat() tentative ${err.attemptNumber} échouée (${err.retriesLeft} restantes)`,
            { error: err.error?.message },
          );
        },
      },
    );
  }

  async *streamChat(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string> {
    const res = await pRetry(
      async () => {
        const r = await net.fetch(`${this.host}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: this.model,
            messages,
            stream: true,
            options: {
              temperature: options?.temperature ?? 0.7,
              num_predict: options?.maxTokens,
            },
            format: options?.jsonMode ? "json" : undefined,
          }),
          signal: AbortSignal.timeout(300_000),
        });
        if (!r.ok) {
          if (r.status >= 400 && r.status < 500) {
            throw new AbortError(`HTTP ${r.status}`);
          }
          throw new Error(`HTTP ${r.status}`);
        }
        return r;
      },
      {
        retries: 3,
        factor: 2,
        minTimeout: 1000,
        onFailedAttempt: (err) => {
          logger.warn(
            `[OllamaProvider] streamChat() tentative ${err.attemptNumber} échouée (${err.retriesLeft} restantes)`,
            { error: err.error?.message },
          );
        },
      },
    );
    const reader = res.body?.getReader();
    if (!reader) {throw new Error("No response body");}
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) {break;}
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n").filter(Boolean);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        try {
          const parsed = JSON.parse(line);
          if (parsed.message?.content) {
            yield parsed.message.content;
          }
        } catch {
          // incomplete JSON line, skip
        }
      }
    }
  }

  async embeddings(texts: string[]): Promise<number[][]> {
    // T13 : Tentative d'appel batch via /api/embed (Ollama 0.5+)
    try {
      const res = await net.fetch(`${this.host}/api/embed`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: this.model, input: texts }),
        signal: AbortSignal.timeout(120_000),
      });
      if (res.ok) {
        const data = (await res.json()) as { embeddings: number[][] };
        if (data.embeddings?.length === texts.length) {
          return data.embeddings;
        }
      }
    } catch {
      // Fallback: per-text /api/embeddings
    }

    // Fallback: process one by one via /api/embeddings
    const results: number[][] = [];
    for (const text of texts) {
      const embedding = await pRetry(
        async () => {
          const res = await net.fetch(`${this.host}/api/embeddings`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model: this.model, prompt: text }),
            signal: AbortSignal.timeout(60_000),
          });
          if (!res.ok) {
            if (res.status >= 400 && res.status < 500) {
              throw new AbortError(`HTTP ${res.status}`);
            }
            throw new Error(`HTTP ${res.status}`);
          }
          const data = await res.json();
          return data.embedding as number[];
        },
        {
          retries: 3,
          factor: 2,
          minTimeout: 1000,
          onFailedAttempt: (err) => {
            logger.warn(
              `[OllamaProvider] embeddings() tentative ${err.attemptNumber} échouée (${err.retriesLeft} restantes)`,
              { error: err.error?.message },
            );
          },
        },
      );
      results.push(embedding);
    }
    return results;
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

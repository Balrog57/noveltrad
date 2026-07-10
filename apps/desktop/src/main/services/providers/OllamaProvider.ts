import { net } from "electron";
import pRetry, { AbortError } from "p-retry";
import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
} from "@shared/types/index.js";
import { logger } from "../../utils/logger.js";

/**
 * SDD §3.7 : Gestion réactive du HTTP 429 (Too Many Requests).
 *
 * En cas de 429, on respecte l'en-tête `Retry-After` (en secondes), on attend,
 * puis on lève une Error simple (PAS AbortError) pour que le pRetry de
 * l'AiRouter retraite la requête. Sans Retry-After, on lève quand même une
 * Error retryable (backoff par défaut du pRetry).
 *
 * Ollama (local) ne retourne normalement pas de 429, mais cette logique
 * s'applique aussi au OpenAiCompatibleProvider via le même pattern.
 */
async function handle429(res: Response): Promise<never> {
  const retryAfter = res.headers.get("Retry-After");
  if (retryAfter) {
    const seconds = Number.parseInt(retryAfter, 10);
    if (Number.isFinite(seconds) && seconds > 0 && seconds < 300) {
      logger.warn(`[Provider] HTTP 429, attente Retry-After: ${seconds}s`);
      await new Promise((r) => setTimeout(r, seconds * 1000));
    }
  }
  // Error retryable (pas AbortError) → pRetry va retry
  throw new Error(`HTTP 429 Too Many Requests`);
}

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
    // SDD §7.10 : le retry réseau est géré au niveau AiRouter (couche
    // orchestration) pour éviter un double-retry (AiRouter × Provider)
    // qui multiplierait les tentatives par 16. Ce provider n'effectue
    // qu'un seul appel ; les erreurs 4xx/5xx remontent à AiRouter qui
    // décide du retry (4xx = AbortError, pas de retry).
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
      if (res.status === 429) {
        // SDD §3.7 : 429 retryable (Retry-After honoré). handle429 throw
        // systématiquement (Error) pour signaler le retry à pRetry. La
        // structure 4xx ci-dessous n'est jamais atteinte pour un 429 — si
        // handle429 est un jour refactoré pour ne pas throw, le 429
        // tomberait dans la branche 4xx et lancerait AbortError
        // (non-retryable), cassant le retry. handle429 est documenté comme
        // retournant never (toujours throw).
        await handle429(res);
      }
      if (res.status >= 400 && res.status < 500) {
        // 4xx : erreur client, ne pas retry (propagé comme AbortError via AiRouter)
        throw new AbortError(`HTTP ${res.status}`);
      }
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    return data.message.content;
  }

  async *streamChat(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string> {
    // SDD §7.10 : retry géré au niveau AiRouter (connexion stream uniquement).
    const res = await net.fetch(`${this.host}/api/chat`, {
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
    if (!res.ok) {
      if (res.status === 429) {
        // SDD §3.7 : 429 retryable (Retry-After honoré)
        await handle429(res);
      }
      if (res.status >= 400 && res.status < 500) {
        throw new AbortError(`HTTP ${res.status}`);
      }
      throw new Error(`HTTP ${res.status}`);
    }
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
            if (res.status === 429) {
              // SDD §3.7 : 429 retryable (Retry-After honoré)
              await handle429(res);
            }
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

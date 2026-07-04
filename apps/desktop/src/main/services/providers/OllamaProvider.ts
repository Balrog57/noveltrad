import { net } from "electron";
import type {
  AiProvider,
  ChatMessage,
  ChatOptions,
} from "@shared/types/index.js";

export class OllamaProvider implements AiProvider {
  constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly model: string,
    public readonly host: string = "http://localhost:11434",
  ) {}

  async listModels(): Promise<string[]> {
    const res = await net.fetch(`${this.host}/api/tags`, { signal: AbortSignal.timeout(10_000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.models.map((m: { name: string }) => m.name);
  }

  async chat(messages: ChatMessage[], options?: ChatOptions): Promise<string> {
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
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.message.content;
  }

  async *streamChat(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string> {
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
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
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
    const results: number[][] = [];
    for (const text of texts) {
      const res = await net.fetch(`${this.host}/api/embeddings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: this.model, prompt: text }),
        signal: AbortSignal.timeout(60_000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      results.push(data.embedding);
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

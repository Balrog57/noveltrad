import type { SettingsManager } from "./SettingsManager.js";
import type { OllamaModelInfo } from "@shared/types/index.js";
import { net } from "electron";
import { logger } from "../utils/logger.js";

export class OllamaManager {
  constructor(private settings: SettingsManager) {}

  private getHost(): string {
    return this.settings.get("ollamaHost") || "http://localhost:11434";
  }

  async isAvailable(): Promise<boolean> {
    const host = this.getHost();
    const url = `${host}/api/tags`;
    logger.debug(`[Ollama] isAvailable() called, url=${url}`);

    try {
      const res = await net.fetch(url, { signal: AbortSignal.timeout(5000) });
      logger.debug(`[Ollama] fetch response: status=${res.status}, ok=${res.ok}`);
      if (!res.ok) {
        logger.debug(`[Ollama] Not OK, returning false`);
        return false;
      }
      const text = await res.text();
      const parsed = JSON.parse(text);
      logger.debug(`[Ollama] Connection successful (${parsed.models?.length ?? 0} models)`);
      return true;
    } catch (e) {
      logger.debug(`[Ollama] Connection FAILED: ${(e as Error).message}`, e as Error);
      return false;
    }
  }

  async listModels(): Promise<OllamaModelInfo[]> {
    const host = this.getHost();
    const res = await net.fetch(`${host}/api/tags`, { signal: AbortSignal.timeout(10000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const parsed = await res.json();
    return (parsed.models ?? []).map((m: { name: string; size: number; details?: { parameter_size?: string; quantization_level?: string } }) => ({
      name: m.name,
      size: m.size,
      parameterSize: m.details?.parameter_size,
      quantizationLevel: m.details?.quantization_level,
    }));
  }

  async pullModel(
    name: string,
    onProgress?: (progress: {
      completed?: number;
      total?: number;
      status: string;
    }) => void,
  ): Promise<void> {
    const host = this.getHost();
    const url = `${host}/api/pull`;
    const res = await net.fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, stream: true }),
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
          const progress = JSON.parse(line);
          onProgress?.(progress);
          if (progress.status === "success") return;
        } catch { /* ignore partial lines */ }
      }
    }
  }

  /** SDD §2.5 : envoie une courte requête pour vérifier que le modèle répond */
  async testModel(name: string): Promise<string> {
    const host = this.getHost();
    const url = `${host}/api/chat`;
    const res = await net.fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: name,
        messages: [{ role: "user", content: "Réponds uniquement par 'ok'." }],
        stream: false,
      }),
      signal: AbortSignal.timeout(120_000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const parsed = await res.json();
    return parsed.message?.content ?? "";
  }
}

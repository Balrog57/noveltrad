import { Ollama } from "ollama";
import type { SettingsManager } from "./SettingsManager.js";
import type { OllamaModelInfo } from "@shared/types/index.js";

export class OllamaManager {
  constructor(private settings: SettingsManager) {}

  private getClient(): Ollama {
    const host = this.settings.get("ollamaHost") || "http://localhost:11434";
    return new Ollama({ host });
  }

  async isAvailable(): Promise<boolean> {
    try {
      const client = this.getClient();
      await client.list();
      return true;
    } catch {
      return false;
    }
  }

  async listModels(): Promise<OllamaModelInfo[]> {
    const client = this.getClient();
    const response = await client.list();
    return response.models.map((m) => ({
      name: m.name,
      size: m.size,
      parameterSize: (m.details as { parameter_size?: string })?.parameter_size,
      quantizationLevel: (m.details as { quantization_level?: string })
        ?.quantization_level,
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
    const client = this.getClient();
    const stream = await client.pull({ model: name, stream: true });
    for await (const chunk of stream) {
      onProgress?.(
        chunk as { completed?: number; total?: number; status: string },
      );
    }
  }

  /** SDD §2.5 : envoie une courte requête pour vérifier que le modèle répond */
  async testModel(name: string): Promise<string> {
    const client = this.getClient();
    const response = await client.chat({
      model: name,
      messages: [{ role: "user", content: "Réponds uniquement par 'ok'." }],
      stream: false,
    });
    return response.message.content;
  }
}

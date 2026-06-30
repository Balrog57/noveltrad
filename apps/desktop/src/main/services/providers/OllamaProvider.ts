import { Ollama } from 'ollama'
import type { AiProvider, ChatMessage, ChatOptions } from '@shared/types/index.js'

export class OllamaProvider implements AiProvider {
  private client: Ollama

  constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly model: string,
    public readonly host: string = 'http://localhost:11434'
  ) {
    this.client = new Ollama({ host })
  }

  async listModels(): Promise<string[]> {
    const response = await this.client.list()
    return response.models.map((m) => m.name)
  }

  async chat(messages: ChatMessage[], options?: ChatOptions): Promise<string> {
    const response = await this.client.chat({
      model: this.model,
      messages,
      stream: false,
      options: {
        temperature: options?.temperature ?? 0.7
      },
      format: options?.jsonMode ? 'json' : undefined
    })
    return response.message.content
  }

  async *streamChat(messages: ChatMessage[], options?: ChatOptions): AsyncIterable<string> {
    const stream = await this.client.chat({
      model: this.model,
      messages,
      stream: true,
      options: {
        temperature: options?.temperature ?? 0.7
      },
      format: options?.jsonMode ? 'json' : undefined
    })
    for await (const chunk of stream) {
      yield chunk.message.content
    }
  }

  async embeddings(texts: string[]): Promise<number[][]> {
    const results: number[][] = []
    for (const text of texts) {
      const response = await this.client.embeddings({ model: this.model, prompt: text })
      results.push(response.embedding as number[])
    }
    return results
  }

  async isAvailable(): Promise<boolean> {
    try {
      await this.listModels()
      return true
    } catch {
      return false
    }
  }
}

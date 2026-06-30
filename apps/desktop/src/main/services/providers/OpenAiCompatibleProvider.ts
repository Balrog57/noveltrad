import OpenAI from 'openai'
import type { AiProvider, ChatMessage, ChatOptions } from '@shared/types/index.js'

export class OpenAiCompatibleProvider implements AiProvider {
  private client: OpenAI

  constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly model: string,
    public readonly baseURL: string,
    public readonly apiKey?: string
  ) {
    this.client = new OpenAI({ baseURL, apiKey })
  }

  async listModels(): Promise<string[]> {
    const response = await this.client.models.list()
    return response.data.map((m) => m.id)
  }

  async chat(messages: ChatMessage[], options?: ChatOptions): Promise<string> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature ?? 0.7,
      response_format: options?.jsonMode ? { type: 'json_object' } : undefined
    })
    return response.choices[0]?.message?.content ?? ''
  }

  async *streamChat(messages: ChatMessage[], options?: ChatOptions): AsyncIterable<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature ?? 0.7,
      stream: true,
      response_format: options?.jsonMode ? { type: 'json_object' } : undefined
    })
    for await (const chunk of stream) {
      yield chunk.choices[0]?.delta?.content ?? ''
    }
  }

  async embeddings(texts: string[]): Promise<number[][]> {
    const response = await this.client.embeddings.create({
      model: this.model,
      input: texts
    })
    return response.data.map((d) => d.embedding)
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

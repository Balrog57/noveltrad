import type { AiProvider, ChatMessage, ChatOptions } from '@shared/types/index.js'

export class AiRouter {
  private providers: Map<string, AiProvider> = new Map()

  register(provider: AiProvider): void {
    this.providers.set(provider.id, provider)
  }

  get(id: string): AiProvider {
    const provider = this.providers.get(id)
    if (!provider) throw new Error(`Provider inconnu : ${id}`)
    return provider
  }

  async chat(providerId: string, messages: ChatMessage[], options?: ChatOptions): Promise<string> {
    return this.get(providerId).chat(messages, options)
  }

  async *streamChat(providerId: string, messages: ChatMessage[], options?: ChatOptions): AsyncIterable<string> {
    yield* this.get(providerId).streamChat(messages, options)
  }
}

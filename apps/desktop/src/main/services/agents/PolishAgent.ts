import type { Agent, AgentConfig } from './Agent.js'
import type { AgentInput, AgentOutput } from '@shared/types/index.js'
import type { AiRouter } from '../AiRouter.js'

export class PolishAgent implements Agent {
  readonly id = 'polish'
  readonly name = 'Polish'
  readonly stage = 'polish'

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? ''
    const prompt = `Perform a final editorial pass on the following ${input.options?.targetLanguage ?? 'French'} text.
Ensure natural rhythm, consistent dialogue, and no artificial language tics. Output only the polished text, nothing else.

${text}`

    const response = await this.aiRouter.chat(this.config.providerId, [{ role: 'user', content: prompt }])
    return { text: response.trim() }
  }
}

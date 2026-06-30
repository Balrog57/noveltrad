import type { Agent, AgentConfig } from './Agent.js'
import type { AgentInput, AgentOutput } from '@shared/types/index.js'
import type { AiRouter } from '../AiRouter.js'

export class GrammarAgent implements Agent {
  readonly id = 'grammar'
  readonly name = 'Grammaire'
  readonly stage = 'grammar'

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? ''
    const prompt = `Proofread the following ${input.options?.targetLanguage ?? 'French'} text for grammar, spelling and punctuation.
Output only the corrected text, nothing else.

${text}`

    const response = await this.aiRouter.chat(this.config.providerId, [{ role: 'user', content: prompt }])
    return { text: response.trim() }
  }
}

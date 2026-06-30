import type { Agent, AgentConfig } from './Agent.js'
import type { AgentInput, AgentOutput } from '@shared/types/index.js'
import type { AiRouter } from '../AiRouter.js'

export class StyleAgent implements Agent {
  readonly id = 'style'
  readonly name = 'Style'
  readonly stage = 'style'

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? ''
    const prompt = `Rewrite the following ${input.options?.targetLanguage ?? 'French'} text to improve flow and remove awkward phrasing or literal translations.
Keep the original meaning and genre tone. Output only the rewritten text, nothing else.

${text}`

    const response = await this.aiRouter.chat(this.config.providerId, [{ role: 'user', content: prompt }])
    return { text: response.trim() }
  }
}

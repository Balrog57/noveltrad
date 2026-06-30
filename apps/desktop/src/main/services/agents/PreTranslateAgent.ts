import type { Agent, AgentConfig } from './Agent.js'
import type { AgentInput, AgentOutput, Paragraph } from '@shared/types/index.js'
import type { AiRouter } from '../AiRouter.js'

export class PreTranslateAgent implements Agent {
  readonly id = 'pre_translate'
  readonly name = 'Pré-traduction'
  readonly stage = 'pre_translate'

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? []
    const sourceLines = paragraphs.map((p) => p.sourceText).join('\n\n')

    const prompt = `Translate the following ${input.options?.sourceLanguage ?? 'text'} paragraphs literally into ${input.options?.targetLanguage ?? 'French'}.
Keep names as written. Output one paragraph per line, same count and order as input.
Do not add explanations.

${sourceLines}`

    const response = await this.aiRouter.chat(this.config.providerId, [
      { role: 'user', content: prompt }
    ])

    const translatedLines = response.split(/\n\n+/).map((t) => t.trim()).filter(Boolean)
    const result: Paragraph[] = paragraphs.map((p, i) => ({
      ...p,
      preTranslatedText: translatedLines[i] ?? ''
    }))

    return { paragraphs: result }
  }
}

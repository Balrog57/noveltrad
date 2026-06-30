import type { Agent, AgentConfig } from './Agent.js'
import type { AgentInput, AgentOutput, Paragraph } from '@shared/types/index.js'

export class SplitAgent implements Agent {
  readonly id = 'split'
  readonly name = 'Découpage'
  readonly stage = 'split'

  constructor(private config: AgentConfig) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const text = input.text ?? ''
    const paragraphs = text
      .split(/\n\n+/)
      .map((t) => t.trim())
      .filter(Boolean)
      .map((sourceText, index): Paragraph => ({
        id: crypto.randomUUID(),
        chapterId: input.chapterId ?? '',
        indexInChapter: index + 1,
        sourceText,
        translatedText: undefined,
        status: 'pending'
      }))

    return { paragraphs }
  }
}

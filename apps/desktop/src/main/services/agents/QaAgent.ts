import type { Agent, AgentConfig } from './Agent.js'
import type { AgentInput, AgentOutput, QualityReport } from '@shared/types/index.js'
import type { AiRouter } from '../AiRouter.js'
import type { QualityChecker } from '../QualityChecker.js'

export class QaAgent implements Agent {
  readonly id = 'qa'
  readonly name = 'QA'
  readonly stage = 'qa'

  constructor(
    private config: AgentConfig,
    private aiRouter: AiRouter,
    private qualityChecker: QualityChecker
  ) {}

  async execute(input: AgentInput): Promise<AgentOutput> {
    const paragraphs = input.paragraphs ?? []
    const sourceText = paragraphs.map((p) => p.sourceText).join('\n\n')
    const translatedText = paragraphs.map((p) => p.translatedText ?? '').join('\n\n')

    const report = await this.qualityChecker.evaluate(sourceText, translatedText, input.lexicon ?? [])
    return { report, score: report.globalScore }
  }
}

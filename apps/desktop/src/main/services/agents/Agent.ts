import type { AgentInput, AgentOutput, WorkflowStage } from '@shared/types/index.js'

export interface Agent {
  readonly id: string
  readonly name: string
  readonly stage: WorkflowStage
  readonly defaultModel?: string

  execute(input: AgentInput): Promise<AgentOutput>
}

export interface AgentConfig {
  providerId: string
  model: string
  temperature?: number
  maxTokens?: number
}

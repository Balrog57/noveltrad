import { describe, it, expect } from 'vitest'
import { LexiconEngine } from '../../src/main/services/LexiconEngine'
import { ConsistencyChecker } from '../../src/main/services/ConsistencyChecker'
import { QualityChecker } from '../../src/main/services/QualityChecker'
import { SplitAgent } from '../../src/main/services/agents/SplitAgent'

describe('LexiconEngine', () => {
  it('applies locked terms', () => {
    const engine = new LexiconEngine()
    const result = engine.apply('The dragon flew.', [
      {
        id: '1',
        projectId: 'p1',
        term: 'dragon',
        translation: 'dragon',
        category: 'creature',
        aliases: [],
        locked: true,
        priority: 10
      }
    ])
    expect(result.text).toBe('The dragon flew.')
    expect(result.substitutions.length).toBe(1)
  })
})

describe('ConsistencyChecker', () => {
  it('reports paragraph count mismatch', () => {
    const checker = new ConsistencyChecker()
    const report = checker.check(['a', 'b'], ['a'], [])
    expect(report.warnings.length).toBeGreaterThan(0)
    expect(report.globalScore).toBeLessThan(100)
  })
})

describe('QualityChecker', () => {
  it('returns a quality report', async () => {
    const checker = new QualityChecker()
    const report = await checker.evaluate('hello world', 'bonjour le monde', [])
    expect(report.globalScore).toBeGreaterThanOrEqual(0)
    expect(report.globalScore).toBeLessThanOrEqual(100)
  })
})

describe('SplitAgent', () => {
  it('splits text into paragraphs', async () => {
    const agent = new SplitAgent({ providerId: 'test', model: 'test' })
    const output = await agent.execute({
      projectId: 'p1',
      text: 'First paragraph.\n\nSecond paragraph.'
    })
    expect(output.paragraphs?.length).toBe(2)
  })
})

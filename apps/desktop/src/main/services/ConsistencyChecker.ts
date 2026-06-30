import type { ConsistencyReport, LexiconEntry } from '@shared/types/index.js'

export class ConsistencyChecker {
  check(source: string[], target: string[], lexicon: LexiconEntry[]): ConsistencyReport {
    const metrics = [
      { name: 'paragraphs', source: source.length, target: target.length, ok: source.length === target.length }
    ]

    const warnings: ConsistencyReport['warnings'] = []
    if (source.length !== target.length) {
      warnings.push({ severity: 'high', message: `Nombre de paragraphes different : ${source.length} source, ${target.length} cible` })
    }

    for (const entry of lexicon.filter((e) => e.locked)) {
      const pattern = new RegExp(`\\b${this.escapeRegExp(entry.term)}\\b`, 'gi')
      const sourceMatches = source.join(' ').match(pattern) ?? []
      const targetMatches = target.join(' ').match(pattern) ?? []
      if (sourceMatches.length > 0 && targetMatches.length === 0) {
        warnings.push({ severity: 'high', message: `Terme verrouille "${entry.term}" absent de la cible` })
      }
    }

    const globalScore = warnings.length === 0 ? 100 : Math.max(0, 100 - warnings.length * 15)

    return { metrics, warnings, globalScore }
  }

  private escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  }
}

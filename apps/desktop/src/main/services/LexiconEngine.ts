import type { LexiconEntry, LexiconApplyResult, Substitution } from '@shared/types/index.js'

export class LexiconEngine {
  private entries: Map<string, LexiconEntry> = new Map()

  load(entries: LexiconEntry[]): void {
    this.entries.clear()
    for (const entry of entries) {
      this.entries.set(entry.term.toLowerCase(), entry)
      for (const alias of entry.aliases) {
        this.entries.set(alias.toLowerCase(), entry)
      }
    }
  }

  apply(text: string, entries?: LexiconEntry[]): LexiconApplyResult {
    const substitutions: Substitution[] = []
    const sorted = entries ? [...entries].sort((a, b) => b.term.length - a.term.length) : Array.from(this.entries.values()).sort((a, b) => b.term.length - a.term.length)

    let result = text
    for (const entry of sorted) {
      const pattern = new RegExp(`\\b${this.escapeRegExp(entry.term)}\\b`, 'gi')
      result = result.replace(pattern, (match) => {
        substitutions.push({ before: match, after: entry.translation, locked: entry.locked })
        return entry.translation
      })
    }

    return { text: result, substitutions }
  }

  private escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  }
}



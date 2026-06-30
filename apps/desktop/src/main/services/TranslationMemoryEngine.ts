import type { TranslationMemoryMatch } from '@shared/types/index.js'
import type { Database } from 'node-sqlite3-wasm'

export class TranslationMemoryEngine {
  constructor(private db?: Database) {}

  setDatabase(db: Database): void {
    this.db = db
  }

  exactMatch(text: string, projectId: string): string | null {
    if (!this.db) return null
    const row = this.db.prepare('SELECT target_text FROM translation_memory WHERE project_id = ? AND source_text = ?').get([projectId, text]) as { target_text: string } | undefined
    return row?.target_text ?? null
  }

  fuzzyMatches(text: string, projectId: string, limit = 5): TranslationMemoryMatch[] {
    if (!this.db) return []
    const rows = this.db.prepare('SELECT source_text, target_text, usage_count FROM translation_memory WHERE project_id = ?').all([projectId]) as Array<{ source_text: string; target_text: string; usage_count: number }>
    return rows
      .map((r) => ({
        sourceText: r.source_text,
        targetText: r.target_text,
        usageCount: r.usage_count,
        similarity: this.levenshteinRatio(text, r.source_text)
      }))
      .filter((m) => m.similarity > 0.85)
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, limit)
  }

  store(source: string, target: string, projectId: string, sourceLanguage: string, targetLanguage: string): void {
    if (!this.db) return
    const existing = this.db.prepare('SELECT id FROM translation_memory WHERE project_id = ? AND source_text = ?').get([projectId, source]) as { id: string } | undefined
    if (existing) {
      this.db.prepare('UPDATE translation_memory SET target_text = ?, usage_count = usage_count + 1, last_used_at = ? WHERE id = ?')
        .run([target, new Date().toISOString(), existing.id])
    } else {
      this.db.prepare('INSERT INTO translation_memory (id, project_id, source_text, target_text, source_language, target_language, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)')
        .run([crypto.randomUUID(), projectId, source, target, sourceLanguage, targetLanguage, new Date().toISOString()])
    }
  }

  private levenshteinRatio(a: string, b: string): number {
    const distance = this.levenshtein(a, b)
    const maxLen = Math.max(a.length, b.length)
    return maxLen === 0 ? 1 : 1 - distance / maxLen
  }

  private levenshtein(a: string, b: string): number {
    const matrix: number[][] = []
    for (let i = 0; i <= b.length; i++) {
      matrix[i] = [i]
    }
    for (let j = 0; j <= a.length; j++) {
      matrix[0][j] = j
    }
    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        const cost = b[i - 1] === a[j - 1] ? 0 : 1
        matrix[i][j] = Math.min(
          matrix[i - 1][j] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j - 1] + cost
        )
      }
    }
    return matrix[b.length][a.length]
  }
}

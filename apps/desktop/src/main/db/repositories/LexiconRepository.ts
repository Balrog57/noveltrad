import type { Database } from 'node-sqlite3-wasm'
import type { LexiconEntry } from '@shared/types/index.js'

export class LexiconRepository {
  constructor(private db: Database) {}

  create(entry: LexiconEntry): void {
    this.db.prepare(`
      INSERT INTO lexicon (id, project_id, term, translation, category, aliases, locked, forbidden, priority, description, notes)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run([
      entry.id,
      entry.projectId,
      entry.term,
      entry.translation,
      entry.category,
      entry.aliases.join('|'),
      entry.locked ? 1 : 0,
      entry.forbidden ? entry.forbidden.join('|') : null,
      entry.priority,
      entry.description ?? null,
      entry.notes ?? null
    ])
  }

  listByProject(projectId: string): LexiconEntry[] {
    const rows = this.db.prepare('SELECT * FROM lexicon WHERE project_id = ? ORDER BY priority DESC, term ASC').all([projectId]) as Record<string, unknown>[]
    return rows.map((r) => this.map(r))
  }

  update(entry: LexiconEntry): void {
    this.db.prepare(`
      UPDATE lexicon SET term = ?, translation = ?, category = ?, aliases = ?, locked = ?, forbidden = ?, priority = ?, description = ?, notes = ?
      WHERE id = ?
    `).run([
      entry.term,
      entry.translation,
      entry.category,
      entry.aliases.join('|'),
      entry.locked ? 1 : 0,
      entry.forbidden ? entry.forbidden.join('|') : null,
      entry.priority,
      entry.description ?? null,
      entry.notes ?? null,
      entry.id
    ])
  }

  delete(id: string): void {
    this.db.prepare('DELETE FROM lexicon WHERE id = ?').run([id])
  }

  private map(row: Record<string, unknown>): LexiconEntry {
    return {
      id: String(row.id),
      projectId: String(row.project_id),
      term: String(row.term),
      translation: String(row.translation),
      category: String(row.category),
      aliases: row.aliases ? String(row.aliases).split('|') : [],
      locked: Boolean(row.locked),
      forbidden: row.forbidden ? String(row.forbidden).split('|') : undefined,
      priority: Number(row.priority),
      description: row.description ? String(row.description) : undefined,
      notes: row.notes ? String(row.notes) : undefined
    }
  }
}

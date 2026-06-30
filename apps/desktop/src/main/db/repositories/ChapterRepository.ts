import type { Database } from 'node-sqlite3-wasm'
import type { Chapter } from '@shared/types/index.js'

export class ChapterRepository {
  constructor(private db: Database) {}

  create(chapter: Chapter): void {
    this.db.prepare(`
      INSERT INTO chapters (id, project_id, title, source_path, order_index, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run([
      chapter.id,
      chapter.projectId,
      chapter.title ?? null,
      chapter.sourcePath ?? null,
      chapter.orderIndex,
      chapter.status,
      chapter.createdAt,
      chapter.updatedAt
    ])
  }

  getById(id: string): Chapter | undefined {
    const row = this.db.prepare('SELECT * FROM chapters WHERE id = ?').get([id]) as Record<string, unknown> | undefined
    if (!row) return undefined
    return this.map(row)
  }

  listByProject(projectId: string): Chapter[] {
    const rows = this.db.prepare('SELECT * FROM chapters WHERE project_id = ? ORDER BY order_index').all([projectId]) as Record<string, unknown>[]
    return rows.map((r) => this.map(r))
  }

  updateStatus(id: string, status: Chapter['status']): void {
    this.db.prepare('UPDATE chapters SET status = ?, updated_at = ? WHERE id = ?').run([status, new Date().toISOString(), id])
  }

  private map(row: Record<string, unknown>): Chapter {
    return {
      id: String(row.id),
      projectId: String(row.project_id),
      title: row.title ? String(row.title) : undefined,
      sourcePath: row.source_path ? String(row.source_path) : undefined,
      orderIndex: Number(row.order_index),
      status: String(row.status) as Chapter['status'],
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at)
    }
  }
}

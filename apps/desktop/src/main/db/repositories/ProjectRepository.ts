import type { Database } from 'node-sqlite3-wasm'
import type { Project } from '@shared/types/index.js'

export class ProjectRepository {
  constructor(private db: Database) {}

  create(project: Project): void {
    const stmt = this.db.prepare(`
      INSERT INTO projects (id, name, author, source_language, target_language, path, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `)
    stmt.run([
      project.id,
      project.name,
      project.author ?? null,
      project.sourceLanguage,
      project.targetLanguage,
      project.path,
      project.createdAt,
      project.updatedAt
    ])
  }

  getByPath(projectPath: string): Project | undefined {
    const row = this.db.prepare('SELECT * FROM projects WHERE path = ?').get([projectPath]) as Record<string, unknown> | undefined
    if (!row) return undefined
    return this.map(row)
  }

  getById(id: string): Project | undefined {
    const row = this.db.prepare('SELECT * FROM projects WHERE id = ?').get([id]) as Record<string, unknown> | undefined
    if (!row) return undefined
    return this.map(row)
  }

  listAll(): Project[] {
    const rows = this.db.prepare('SELECT * FROM projects ORDER BY updated_at DESC').all() as Record<string, unknown>[]
    return rows.map((r) => this.map(r))
  }

  delete(id: string): void {
    this.db.prepare('DELETE FROM projects WHERE id = ?').run([id])
  }

  private map(row: Record<string, unknown>): Project {
    return {
      id: String(row.id),
      name: String(row.name),
      author: row.author ? String(row.author) : undefined,
      sourceLanguage: String(row.source_language),
      targetLanguage: String(row.target_language),
      path: String(row.path),
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at)
    }
  }
}

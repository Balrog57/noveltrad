import type { Chapter } from "@shared/types/index.js";
import type { Database } from "node-sqlite3-wasm";
import { BaseRepository } from "../base/BaseRepository.js";

/**
 * WS-1 (clean architecture) : hérite de `BaseRepository<Chapter>`.
 * `findById`/`deleteById` de la base couvrent l'ancien `getById`/`delete`,
 * mais Chapter est supprimée en cascade via project — pas de `delete` public ici.
 */
export class ChapterRepository extends BaseRepository<Chapter> {
  constructor(db: Database) {
    super(db, "chapters");
  }

  create(chapter: Chapter): void {
    this.execute(
      `
      INSERT INTO chapters (id, project_id, title, source_path, order_index, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `,
      [
        chapter.id,
        chapter.projectId,
        chapter.title ?? null,
        chapter.sourcePath ?? null,
        chapter.orderIndex,
        chapter.status,
        chapter.createdAt,
        chapter.updatedAt,
      ],
    );
  }

  getById(id: string): Chapter | undefined {
    return this.findById(id);
  }

  listByProject(projectId: string): Chapter[] {
    return this.queryMany(
      "SELECT * FROM chapters WHERE project_id = ? ORDER BY order_index",
      [projectId],
    );
  }

  updateStatus(id: string, status: Chapter["status"]): void {
    this.execute(
      "UPDATE chapters SET status = ?, updated_at = ? WHERE id = ?",
      [status, new Date().toISOString(), id],
    );
  }

  protected map(row: Record<string, unknown>): Chapter {
    return {
      id: String(row.id),
      projectId: String(row.project_id),
      title: row.title ? String(row.title) : undefined,
      sourcePath: row.source_path ? String(row.source_path) : undefined,
      orderIndex: Number(row.order_index),
      status: String(row.status) as Chapter["status"],
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at),
    };
  }
}

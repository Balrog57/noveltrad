import type { Project } from "@shared/types/index.js";
import { BaseRepository } from "../base/BaseRepository.js";

/**
 * Repository pour l'entité `Project` (table `projects`).
 *
 * WS-1 (clean architecture) : hérite de `BaseRepository<Project>` pour
 * partager les mécaniques de lecture/écriture. `findById`/`deleteById` de la
 * base correspondent exactement à l'ancien `getById`/`delete` — on expose
 * donc des alias publics qui délèguent, afin de préserver l'API call-site.
 */
export class ProjectRepository extends BaseRepository<Project> {
  constructor(db: import("node-sqlite3-wasm").Database) {
    super(db, "projects");
  }

  create(project: Project): void {
    this.execute(
      `
      INSERT INTO projects (id, name, author, source_language, target_language, path, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `,
      [
        project.id,
        project.name,
        project.author ?? null,
        project.sourceLanguage,
        project.targetLanguage,
        project.path,
        project.createdAt,
        project.updatedAt,
      ],
    );
  }

  getByPath(projectPath: string): Project | undefined {
    return this.queryOne("SELECT * FROM projects WHERE path = ?", [
      projectPath,
    ]);
  }

  getById(id: string): Project | undefined {
    return this.findById(id);
  }

  listAll(): Project[] {
    return this.queryMany(
      "SELECT * FROM projects ORDER BY updated_at DESC",
    );
  }

  delete(id: string): void {
    this.deleteById(id);
  }

  protected map(row: Record<string, unknown>): Project {
    return {
      id: String(row.id),
      name: String(row.name),
      author: row.author ? String(row.author) : undefined,
      sourceLanguage: String(row.source_language),
      targetLanguage: String(row.target_language),
      path: String(row.path),
      createdAt: String(row.created_at),
      updatedAt: String(row.updated_at),
    };
  }
}

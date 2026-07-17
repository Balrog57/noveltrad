import type { Database } from "node-sqlite3-wasm";
import type { ChapterSummary, NovelSummary } from "@shared/types/index.js";
import { randomUUID } from "node:crypto";

/**
 * Repository pour les résumés produits par le SummarizerAgent (v1.4).
 * SDD §7.13 / §8.12 — cohérence cross-chapitre.
 */
export class SummaryRepository {
  constructor(private db: Database) {}

  // ── Chapter summaries ─────────────────────────────────────────────────

  upsertChapterSummary(summary: Omit<ChapterSummary, "id" | "createdAt">): ChapterSummary {
    const id = randomUUID();
    const createdAt = new Date().toISOString();
    this.db
      .prepare(
        `INSERT INTO chapter_summaries (id, chapter_id, project_id, summary, token_count, created_at)
         VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(chapter_id) DO UPDATE SET
           summary = excluded.summary,
           token_count = excluded.token_count`,
      )
      .run([
        id,
        summary.chapterId,
        summary.projectId,
        summary.summary,
        summary.tokenCount ?? null,
        createdAt,
      ]);
    return { ...summary, id, createdAt };
  }

  getChapterSummary(chapterId: string): ChapterSummary | null {
    const row = this.db
      .prepare("SELECT * FROM chapter_summaries WHERE chapter_id = ?")
      .get([chapterId]) as Record<string, unknown> | undefined;
    return row ? this.mapChapter(row) : null;
  }

  listChapterSummaries(projectId: string): ChapterSummary[] {
    const rows = this.db
      .prepare(
        "SELECT * FROM chapter_summaries WHERE project_id = ? ORDER BY created_at ASC",
      )
      .all([projectId]) as Record<string, unknown>[];
    return rows.map((r) => this.mapChapter(r));
  }

  // ── Novel summary (singleton par projet) ──────────────────────────────

  getNovelSummary(projectId: string): NovelSummary | null {
    const row = this.db
      .prepare("SELECT * FROM novel_summaries WHERE project_id = ?")
      .get([projectId]) as Record<string, unknown> | undefined;
    return row ? this.mapNovel(row) : null;
  }

  upsertNovelSummary(projectId: string, summary: string): NovelSummary {
    // P0-4 fix : l'ancienne implémentation était un read-then-write (SELECT
    // puis INSERT/UPDATE) sans transaction → TOCTOU. Deux upserts concurrents
    // (ex: deux WorkflowRunner sur le même projet) pouvaient tous deux prendre
    // la branche INSERT et violer UNIQUE(project_id).
    //
    // Solution : un unique UPSERT atomique via ON CONFLICT, comme
    // upsertChapterSummary. On récupère ensuite la ligne pour connaître la
    // version finale (version + 1 sur update, 1 sur insert).
    const updatedAt = new Date().toISOString();
    this.db
      .prepare(
        `INSERT INTO novel_summaries (id, project_id, summary, version, updated_at)
         VALUES (?, ?, ?, 1, ?)
         ON CONFLICT(project_id) DO UPDATE SET
           summary = excluded.summary,
           version = version + 1,
           updated_at = excluded.updated_at`,
      )
      .run([randomUUID(), projectId, summary, updatedAt]);
    // Re-lecture pour récupérer l'id stable et la version effective.
    return this.getNovelSummary(projectId)!;
  }

  // ── Mapping ───────────────────────────────────────────────────────────

  private mapChapter(row: Record<string, unknown>): ChapterSummary {
    return {
      id: String(row.id),
      chapterId: String(row.chapter_id),
      projectId: String(row.project_id),
      summary: String(row.summary),
      tokenCount: row.token_count != null ? Number(row.token_count) : undefined,
      createdAt: String(row.created_at),
    };
  }

  private mapNovel(row: Record<string, unknown>): NovelSummary {
    return {
      id: String(row.id),
      projectId: String(row.project_id),
      summary: String(row.summary),
      version: Number(row.version),
      updatedAt: String(row.updated_at),
    };
  }
}

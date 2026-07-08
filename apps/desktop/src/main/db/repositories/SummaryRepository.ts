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
    const existing = this.getNovelSummary(projectId);
    const updatedAt = new Date().toISOString();
    if (existing) {
      this.db
        .prepare(
          "UPDATE novel_summaries SET summary = ?, version = version + 1, updated_at = ? WHERE project_id = ?",
        )
        .run([summary, updatedAt, projectId]);
      return {
        ...existing,
        summary,
        version: existing.version + 1,
        updatedAt,
      };
    }
    const id = randomUUID();
    this.db
      .prepare(
        `INSERT INTO novel_summaries (id, project_id, summary, version, updated_at)
         VALUES (?, ?, ?, 1, ?)`,
      )
      .run([id, projectId, summary, updatedAt]);
    return {
      id,
      projectId,
      summary,
      version: 1,
      updatedAt,
    };
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

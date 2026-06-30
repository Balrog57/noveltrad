import type { Database } from "node-sqlite3-wasm";
import type {
  HistorySnapshot,
  Paragraph,
  SnapshotTrigger,
} from "@shared/types/index.js";

export class HistoryRepository {
  constructor(private db: Database) {}

  /**
   * Crée un nouveau snapshot d'historique.
   * `paragraphs` est stocké au format JSON.
   * `triggeredBy` et autres métadonnées sont stockés dans `metadata`.
   */
  create(snapshot: {
    id: string;
    projectId: string;
    chapterId?: string;
    jobId?: string;
    stepId?: string;
    stage: string;
    paragraphs: Paragraph[];
    triggeredBy: SnapshotTrigger;
  }): void {
    const metadata = JSON.stringify({
      triggeredBy: snapshot.triggeredBy,
    });

    this.db
      .prepare(
        `INSERT INTO history_snapshots (id, project_id, chapter_id, job_id, step_id, stage, paragraphs, metadata, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run([
        snapshot.id,
        snapshot.projectId,
        snapshot.chapterId ?? null,
        snapshot.jobId ?? null,
        snapshot.stepId ?? null,
        snapshot.stage,
        JSON.stringify(snapshot.paragraphs),
        metadata,
        new Date().toISOString(),
      ]);
  }

  /**
   * Liste tous les snapshots pour un projet, triés par date décroissante.
   * Effectue une jointure avec `job_steps` pour obtenir le score qualité.
   */
  listByProject(projectId: string): HistorySnapshot[] {
    const rows = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
       FROM history_snapshots hs
       LEFT JOIN job_steps js ON hs.step_id = js.id
       WHERE hs.project_id = ?
       ORDER BY hs.created_at DESC`,
      )
      .all([projectId]) as Record<string, unknown>[];
    return this.mapRows(rows);
  }

  /**
   * Liste les snapshots pour un chapitre donné, triés par date décroissante.
   */
  listByChapter(chapterId: string): HistorySnapshot[] {
    const rows = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
       FROM history_snapshots hs
       LEFT JOIN job_steps js ON hs.step_id = js.id
       WHERE hs.chapter_id = ?
       ORDER BY hs.created_at DESC`,
      )
      .all([chapterId]) as Record<string, unknown>[];
    return this.mapRows(rows);
  }

  /**
   * Récupère un snapshot par son ID.
   */
  getById(id: string): HistorySnapshot | null {
    const row = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
       FROM history_snapshots hs
       LEFT JOIN job_steps js ON hs.step_id = js.id
       WHERE hs.id = ?`,
      )
      .get([id]) as Record<string, unknown> | undefined;
    return row ? this.mapRow(row) : null;
  }

  /**
   * Récupère les paragraphes actuels les plus récents pour un chapitre,
   * depuis le dernier snapshot.
   */
  getLatest(chapterId: string): HistorySnapshot | null {
    const row = this.db
      .prepare(
        `SELECT hs.*, js.score AS step_score
       FROM history_snapshots hs
       LEFT JOIN job_steps js ON hs.step_id = js.id
       WHERE hs.chapter_id = ?
       ORDER BY hs.created_at DESC
       LIMIT 1`,
      )
      .get([chapterId]) as Record<string, unknown> | undefined;
    return row ? this.mapRow(row) : null;
  }

  // ── Helpers privés ──

  private mapRows(rows: Record<string, unknown>[]): HistorySnapshot[] {
    const total = rows.length;
    return rows.map((row, index) => this.mapRow(row, total - index));
  }

  private mapRow(
    row: Record<string, unknown>,
    versionNumber?: number,
  ): HistorySnapshot {
    let metadata: Record<string, unknown> = {};
    const rowMetadata = row.metadata;
    if (rowMetadata) {
      try {
        metadata = JSON.parse(String(rowMetadata)) as Record<string, unknown>;
      } catch {
        metadata = {};
      }
    }

    let paragraphs: Paragraph[] = [];
    try {
      paragraphs = JSON.parse(String(row.paragraphs)) as Paragraph[];
    } catch {
      paragraphs = [];
    }

    const triggeredBy: SnapshotTrigger =
      metadata.triggeredBy === "manual" ||
      metadata.triggeredBy === "rollback" ||
      metadata.triggeredBy === "workflow"
        ? (metadata.triggeredBy as SnapshotTrigger)
        : "workflow";

    const stepScore = row.step_score;

    return {
      id: String(row.id),
      projectId: String(row.project_id),
      chapterId: row.chapter_id ? String(row.chapter_id) : undefined,
      jobId: row.job_id ? String(row.job_id) : undefined,
      stepId: row.step_id ? String(row.step_id) : undefined,
      stage: String(row.stage),
      paragraphs,
      qualityScore: stepScore != null ? Number(stepScore) : undefined,
      triggeredBy,
      createdAt: String(row.created_at),
      versionNumber,
    };
  }
}

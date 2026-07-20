import type { Job, Step } from "@shared/types/index.js";
import type { Database } from "node-sqlite3-wasm";
import { BaseRepository } from "../base/BaseRepository.js";

/**
 * WS-1 (clean architecture) : hérite de `BaseRepository<Job>` (entité primaire).
 * `Step` est une entité secondaire mappée via `mapStep` privé ; les helpers
 * `getStep`/`listStepsByJob` font leur propre SELECT/prepare (table `job_steps`).
 */
export class JobRepository extends BaseRepository<Job> {
  constructor(db: Database) {
    super(db, "jobs");
  }

  createJob(job: Job): void {
    this.execute(
      `
      INSERT INTO jobs (id, project_id, chapter_id, type, status, started_at, finished_at, error_message, created_at, chapter_ids, metadata, cost_usd, qa_retry_count)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
      [
        job.id,
        job.projectId,
        job.chapterId ?? null,
        job.type,
        job.status,
        job.startedAt ?? null,
        job.finishedAt ?? null,
        job.errorMessage ?? null,
        job.createdAt,
        job.chapterIds ? JSON.stringify(job.chapterIds) : null,
        job.metadata ? JSON.stringify(job.metadata) : null,
        job.costUsd ?? null,
        job.qaRetryCount ?? 0,
      ],
    );
  }

  getJob(id: string): Job | undefined {
    return this.findById(id);
  }

  listByProject(projectId: string): Job[] {
    return this.queryMany(
      "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC",
      [projectId],
    );
  }

  /** SDD §7.11 : liste les jobs en cours (running/paused) pour la reprise au démarrage */
  listActive(): Job[] {
    return this.queryMany(
      "SELECT * FROM jobs WHERE status IN ('running', 'paused') ORDER BY created_at DESC",
    );
  }

  updateJob(job: Job): void {
    this.execute(
      `UPDATE jobs SET status = ?, started_at = ?, finished_at = ?, error_message = ?, chapter_ids = ?, metadata = ?, cost_usd = ?, qa_retry_count = ? WHERE id = ?`,
      [
        job.status,
        job.startedAt ?? null,
        job.finishedAt ?? null,
        job.errorMessage ?? null,
        job.chapterIds ? JSON.stringify(job.chapterIds) : null,
        job.metadata ? JSON.stringify(job.metadata) : null,
        job.costUsd ?? null,
        job.qaRetryCount ?? 0,
        job.id,
      ],
    );
  }

  createStep(step: Step): void {
    this.execute(
      `
      INSERT INTO job_steps (id, job_id, agent_id, name, stage, order_index, status, input_snapshot, output_snapshot, score, tokens_in, tokens_out, duration_ms, started_at, finished_at, error_message, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
      [
        step.id,
        step.jobId,
        step.agentId,
        step.name,
        step.stage,
        step.orderIndex,
        step.status,
        step.inputSnapshot ? JSON.stringify(step.inputSnapshot) : null,
        step.outputSnapshot ? JSON.stringify(step.outputSnapshot) : null,
        step.score ?? null,
        step.tokensIn ?? null,
        step.tokensOut ?? null,
        step.durationMs ?? null,
        step.startedAt ?? null,
        step.finishedAt ?? null,
        step.errorMessage ?? null,
        step.createdAt,
      ],
    );
  }

  getStep(id: string): Step | undefined {
    const row = this.db
      .prepare("SELECT * FROM job_steps WHERE id = ?")
      .get([id]) as Record<string, unknown> | undefined;
    return row ? this.mapStep(row) : undefined;
  }

  listStepsByJob(jobId: string): Step[] {
    const rows = this.db
      .prepare("SELECT * FROM job_steps WHERE job_id = ? ORDER BY order_index")
      .all([jobId]) as Record<string, unknown>[];
    return rows.map((r) => this.mapStep(r));
  }

  updateStep(step: Step): void {
    this.execute(
      `
      UPDATE job_steps SET status = ?, input_snapshot = ?, output_snapshot = ?, score = ?, tokens_in = ?, tokens_out = ?, duration_ms = ?, started_at = ?, finished_at = ?, error_message = ?
      WHERE id = ?
    `,
      [
        step.status,
        step.inputSnapshot ? JSON.stringify(step.inputSnapshot) : null,
        step.outputSnapshot ? JSON.stringify(step.outputSnapshot) : null,
        step.score ?? null,
        step.tokensIn ?? null,
        step.tokensOut ?? null,
        step.durationMs ?? null,
        step.startedAt ?? null,
        step.finishedAt ?? null,
        step.errorMessage ?? null,
        step.id,
      ],
    );
  }

  protected map(row: Record<string, unknown>): Job {
    return {
      id: String(row.id),
      projectId: String(row.project_id),
      chapterId: row.chapter_id ? String(row.chapter_id) : undefined,
      chapterIds: row.chapter_ids
        ? (JSON.parse(String(row.chapter_ids)) as string[])
        : undefined,
      type: String(row.type) as Job["type"],
      status: String(row.status) as Job["status"],
      startedAt: row.started_at ? String(row.started_at) : undefined,
      finishedAt: row.finished_at ? String(row.finished_at) : undefined,
      errorMessage: row.error_message ? String(row.error_message) : undefined,
      metadata: row.metadata
        ? (JSON.parse(String(row.metadata)) as Record<string, unknown>)
        : undefined,
      costUsd: row.cost_usd != null ? Number(row.cost_usd) : undefined,
      qaRetryCount: row.qa_retry_count != null ? Number(row.qa_retry_count) : undefined,
      createdAt: String(row.created_at),
    };
  }

  private mapStep(row: Record<string, unknown>): Step {
    return {
      id: String(row.id),
      jobId: String(row.job_id),
      agentId: String(row.agent_id),
      name: String(row.name),
      stage: String(row.stage) as Step["stage"],
      orderIndex: Number(row.order_index),
      status: String(row.status) as Step["status"],
      inputSnapshot: row.input_snapshot
        ? (JSON.parse(String(row.input_snapshot)) as Record<string, unknown>)
        : undefined,
      outputSnapshot: row.output_snapshot
        ? (JSON.parse(String(row.output_snapshot)) as Record<string, unknown>)
        : undefined,
      score: row.score ? Number(row.score) : undefined,
      tokensIn: row.tokens_in ? Number(row.tokens_in) : undefined,
      tokensOut: row.tokens_out ? Number(row.tokens_out) : undefined,
      durationMs: row.duration_ms ? Number(row.duration_ms) : undefined,
      startedAt: row.started_at ? String(row.started_at) : undefined,
      finishedAt: row.finished_at ? String(row.finished_at) : undefined,
      errorMessage: row.error_message ? String(row.error_message) : undefined,
      createdAt: String(row.created_at),
    };
  }
}

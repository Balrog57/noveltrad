import type { Database } from "node-sqlite3-wasm";
import type { Job, Step } from "@shared/types/index.js";

export class JobRepository {
  constructor(private db: Database) {}

  createJob(job: Job): void {
    this.db
      .prepare(
        `
      INSERT INTO jobs (id, project_id, chapter_id, type, status, started_at, finished_at, error_message, created_at, chapter_ids, metadata, cost_usd, qa_retry_count)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
      )
      .run([
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
      ]);
  }

  getJob(id: string): Job | undefined {
    const row = this.db.prepare("SELECT * FROM jobs WHERE id = ?").get([id]) as
      Record<string, unknown> | undefined;
    if (!row) {return undefined;}
    return this.mapJob(row);
  }

  listByProject(projectId: string): Job[] {
    const rows = this.db
      .prepare(
        "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC",
      )
      .all([projectId]) as Record<string, unknown>[];
    return rows.map((r) => this.mapJob(r));
  }

  /** SDD §7.11 : liste les jobs en cours (running/paused) pour la reprise au démarrage */
  listActive(): Job[] {
    const rows = this.db
      .prepare(
        "SELECT * FROM jobs WHERE status IN ('running', 'paused') ORDER BY created_at DESC",
      )
      .all() as Record<string, unknown>[];
    return rows.map((r) => this.mapJob(r));
  }

  updateJob(job: Job): void {
    this.db
      .prepare(
        `UPDATE jobs SET status = ?, started_at = ?, finished_at = ?, error_message = ?, chapter_ids = ?, metadata = ?, cost_usd = ?, qa_retry_count = ? WHERE id = ?`,
      )
      .run([
        job.status,
        job.startedAt ?? null,
        job.finishedAt ?? null,
        job.errorMessage ?? null,
        job.chapterIds ? JSON.stringify(job.chapterIds) : null,
        job.metadata ? JSON.stringify(job.metadata) : null,
        job.costUsd ?? null,
        job.qaRetryCount ?? 0,
        job.id,
      ]);
  }

  createStep(step: Step): void {
    this.db
      .prepare(
        `
      INSERT INTO job_steps (id, job_id, agent_id, name, stage, order_index, status, input_snapshot, output_snapshot, score, tokens_in, tokens_out, duration_ms, started_at, finished_at, error_message, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
      )
      .run([
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
      ]);
  }

  getStep(id: string): Step | undefined {
    const row = this.db
      .prepare("SELECT * FROM job_steps WHERE id = ?")
      .get([id]) as Record<string, unknown> | undefined;
    if (!row) {return undefined;}
    return this.mapStep(row);
  }

  listStepsByJob(jobId: string): Step[] {
    const rows = this.db
      .prepare("SELECT * FROM job_steps WHERE job_id = ? ORDER BY order_index")
      .all([jobId]) as Record<string, unknown>[];
    return rows.map((r) => this.mapStep(r));
  }

  updateStep(step: Step): void {
    this.db
      .prepare(
        `
      UPDATE job_steps SET status = ?, input_snapshot = ?, output_snapshot = ?, score = ?, tokens_in = ?, tokens_out = ?, duration_ms = ?, started_at = ?, finished_at = ?, error_message = ?
      WHERE id = ?
    `,
      )
      .run([
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
      ]);
  }

  private mapJob(row: Record<string, unknown>): Job {
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

"""JobService (SDD 5.8, 12).

Owns the coordinated processing transitions: each take_next, pause, resume,
failure or completion modifies — in one BEGIN IMMEDIATE — the job, its
document, the project and, when applicable, the promotion of the next
Waiting job.
"""

from __future__ import annotations

import sqlite3

from noveltrad.core.clock import utc_now
from noveltrad.core.contracts import (
    DocumentId,
    Job,
    JobId,
    JobState,
    PipelineSnapshot,
    ProjectId,
    ProjectProgress,
    ProjectStatus,
)
from noveltrad.core.exceptions import ConflictError, NotFoundError, ValidationError
from noveltrad.core.logging import LogContext, LogService, new_correlation_id
from noveltrad.core.transactions import UnitOfWork

from .models import to_job
from .repository import JobRepository

_PAUSE_STATES = ("Queued", "Running", "Retrying")


class JobService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        repository: JobRepository,
        logs: LogService,
    ) -> None:
        self._conn = conn
        self._repo = repository
        self._logs = logs

    # -- enqueue ----------------------------------------------------------

    def enqueue_project(self, project_id: ProjectId, snapshot: PipelineSnapshot) -> tuple[Job, ...]:
        """Create the FIFO for all validated documents (12.2)."""
        row = self._conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"project {project_id} not found")
        if row["status"] in (ProjectStatus.RUNNING.value, ProjectStatus.PAUSED.value):
            raise ConflictError("a translation is already active")
        docs = self._conn.execute(
            "SELECT id FROM documents WHERE project_id=? AND status='ToTranslate' "
            "ORDER BY order_index",
            (project_id,),
        ).fetchall()
        if not docs:
            raise ValidationError("no documents to translate")
        jobs: list[Job] = []
        with UnitOfWork(self._conn, immediate=True):
            self._conn.execute(
                "UPDATE projects SET status='Running', updated_at=? WHERE id=?",
                (utc_now().isoformat(), project_id),
            )
            for index, doc in enumerate(docs):
                state = "Queued" if index == 0 else "Waiting"
                row_job = self._repo.insert(DocumentId(int(doc["id"])), snapshot, state)
                jobs.append(to_job(row_job, snapshot))
                if index == 0:
                    self._conn.execute(
                        "UPDATE documents SET status='Running', updated_at=? WHERE id=?",
                        (utc_now().isoformat(), doc["id"]),
                    )
            self._logs.record(
                "INFO",
                "job.enqueue",
                f"{len(jobs)} jobs enqueued",
                LogContext(
                    correlation_id=new_correlation_id(),
                    project_id=project_id,
                    job_id=jobs[0].id,
                ),
            )
        return tuple(jobs)

    # -- worker coordination ----------------------------------------------

    def take_next(self) -> Job | None:
        """Take the FIFO head inside BEGIN IMMEDIATE, guarding one active job."""
        active = self._repo.active_job()
        if active is not None:
            return None
        candidate = self._repo.first_queued()
        if candidate is None:
            return None
        with UnitOfWork(self._conn, immediate=True):
            if candidate.control_request == "PAUSE":
                updated = self._repo.update_state(candidate.id, JobState.PAUSED.value)
                self._pause_document(candidate.document_id)
                self._logs.record(
                    "INFO", "job.pause", "job paused before start", _ctx(candidate.id)
                )
                return to_job(updated, self._snapshot_of(candidate))
            if candidate.next_retry_at is not None and _future(candidate.next_retry_at):
                return None
            updated = self._repo.update_state(
                candidate.id,
                JobState.RUNNING.value,
                started_at=utc_now().isoformat(),
            )
            self._logs.record("INFO", "job.take", "job started", _ctx(candidate.id))
            return to_job(updated, self._snapshot_of(candidate))

    def _snapshot_of(self, row) -> PipelineSnapshot:
        from .repository import deserialize_snapshot

        return deserialize_snapshot(row.snapshot_json, row.snapshot_hash)

    def request_pause(self, project_id: ProjectId) -> None:
        """Request cooperative pause; consumed after the current call (12.5)."""
        rows = self._repo.list_by_project(project_id)
        for row in rows:
            if row.state in _PAUSE_STATES:
                updated = self._repo.request_pause(row.id)
                self._logs.record("INFO", "job.pause", "pause requested", _ctx(row.id))
                del updated

    def resume(self, job_id: JobId) -> Job:
        """Resume from Paused or Failed with the same snapshot (12.15)."""
        row = self._repo.get(job_id)
        if row.state not in (JobState.PAUSED.value, JobState.FAILED.value):
            raise ConflictError(f"job {job_id} is not resumable")
        with UnitOfWork(self._conn, immediate=True):
            if row.state == JobState.FAILED.value:
                row = self._repo.update_state(job_id, JobState.QUEUED.value, next_retry_at=None)
            else:
                row = self._repo.update_state(job_id, JobState.QUEUED.value)
            self._conn.execute(
                "UPDATE documents SET status='ToTranslate', updated_at=? WHERE id=?",
                (utc_now().isoformat(), row.document_id),
            )
            self._conn.execute(
                "UPDATE projects SET status='Running', updated_at=? WHERE id IN "
                "(SELECT project_id FROM documents WHERE id=?)",
                (utc_now().isoformat(), row.document_id),
            )
            self._logs.record("INFO", "job.resume", "job resumed", _ctx(job_id))
        return to_job(row, self._snapshot_of(row))

    def restart_with_current_configuration(self, job_id: JobId, confirmation: str) -> Job:
        """RESTART_DOCUMENT: reset segments to PENDING with a new snapshot (11.16)."""
        if confirmation != "RESTART_DOCUMENT":
            raise ValidationError("confirmation mismatch: expected RESTART_DOCUMENT")
        row = self._repo.get(job_id)
        doc_row = self._conn.execute(
            "SELECT status FROM documents WHERE id=?", (row.document_id,)
        ).fetchone()
        if doc_row is None or doc_row["status"] == "Completed":
            raise ConflictError("RESTART_DOCUMENT is not allowed on a completed document")
        raise ConflictError(
            "RESTART_DOCUMENT requires a tested current configuration "
            "(handled by the caller with the new snapshot)"
        )

    def apply_pause(self, job_id: JobId) -> Job:
        """Apply the cooperative pause after the current call (12.14)."""
        row = self._repo.get(job_id)
        with UnitOfWork(self._conn, immediate=True):
            updated = self._repo.update_state(job_id, JobState.PAUSED.value)
            self._repo.clear_pause_request(job_id)
            self._pause_document(row.document_id)
            self._conn.execute(
                "UPDATE projects SET status='Paused', updated_at=? WHERE id IN "
                "(SELECT project_id FROM documents WHERE id=?)",
                (utc_now().isoformat(), row.document_id),
            )
            self._logs.record("INFO", "job.pause", "job paused", _ctx(job_id))
        return to_job(updated, self._snapshot_of(row))

    def mark_completed(self, job_id: JobId) -> Job:
        """Promote the next Waiting job or complete the project (12.14)."""
        row = self._repo.get(job_id)
        project_id = self._project_of(row.document_id)
        with UnitOfWork(self._conn, immediate=True):
            updated = self._repo.update_state(
                job_id,
                JobState.COMPLETED.value,
                progress=100.0,
                finished_at=utc_now().isoformat(),
            )
            self._conn.execute(
                "UPDATE documents SET status='Completed', progress=100.0, updated_at=? WHERE id=?",
                (utc_now().isoformat(), row.document_id),
            )
            next_job = self._repo.promote_next_waiting(project_id)
            if next_job is None:
                remaining = self._conn.execute(
                    "SELECT COUNT(*) AS c FROM documents WHERE project_id=? "
                    "AND status != 'Completed'",
                    (project_id,),
                ).fetchone()
                if remaining["c"] == 0:
                    self._conn.execute(
                        "UPDATE projects SET status='Completed', updated_at=? WHERE id=?",
                        (utc_now().isoformat(), project_id),
                    )
            self._logs.record("INFO", "job.completed", "job completed", _ctx(job_id))
        return to_job(updated, self._snapshot_of(row))

    def mark_failed(self, job_id: JobId, error_code: str) -> Job:
        """Keep the resume point, promote nothing, unlock recovery (12.14)."""
        row = self._repo.get(job_id)
        project_id = self._project_of(row.document_id)
        with UnitOfWork(self._conn, immediate=True):
            updated = self._repo.update_state(
                job_id,
                JobState.FAILED.value,
                message=f"failed: {error_code}",
                finished_at=utc_now().isoformat(),
            )
            self._conn.execute(
                "UPDATE documents SET status='Failed', updated_at=? WHERE id=?",
                (utc_now().isoformat(), row.document_id),
            )
            self._conn.execute(
                "UPDATE projects SET status='Failed', updated_at=? WHERE id=?",
                (utc_now().isoformat(), project_id),
            )
            self._logs.record(
                "ERROR",
                "job.failed",
                f"job failed: {error_code}",
                _ctx(job_id),
                error_code=error_code,
            )
        return to_job(updated, self._snapshot_of(row))

    def recover_interrupted(self) -> None:
        """Recover Running/Retrying jobs at startup (12.16)."""
        with UnitOfWork(self._conn, immediate=True):
            recovered = self._repo.recover_interrupted()
            for row in recovered:
                self._conn.execute(
                    "UPDATE documents SET status='ToTranslate', updated_at=? WHERE id=?",
                    (utc_now().isoformat(), row.document_id),
                )
                self._logs.record("INFO", "job.resume", "interrupted job recovered", _ctx(row.id))

    # -- progress ---------------------------------------------------------

    def get_progress(self, project_id: ProjectId) -> ProjectProgress:
        row = self._conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"project {project_id} not found")
        docs = self._conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS done "
            "FROM documents WHERE project_id=?",
            (project_id,),
        ).fetchone()
        active = self._repo.active_job()
        active_job = to_job(active, self._snapshot_of(active)) if active else None
        return ProjectProgress(
            project_id=project_id,
            project_status=ProjectStatus(row["status"]),
            active_job=active_job,
            completed_documents=int(docs["done"] or 0),
            total_documents=int(docs["total"] or 0),
            elapsed_seconds=0.0,
            estimated_remaining_seconds=None,
        )

    # -- helpers ----------------------------------------------------------

    def _project_of(self, document_id: DocumentId) -> ProjectId:
        row = self._conn.execute(
            "SELECT project_id FROM documents WHERE id=?", (document_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"document {document_id} not found")
        return ProjectId(int(row["project_id"]))

    def _pause_document(self, document_id: DocumentId) -> None:
        self._conn.execute(
            "UPDATE documents SET status='Paused', updated_at=? WHERE id=?",
            (utc_now().isoformat(), document_id),
        )


def _ctx(job_id: JobId) -> LogContext:
    return LogContext(correlation_id=new_correlation_id(), job_id=job_id)


def _future(iso: str) -> bool:
    from datetime import UTC, datetime

    return datetime.fromisoformat(iso).astimezone(UTC) > utc_now()

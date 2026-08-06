"""Job persistence (SDD 8.7). FIFO ordering by (queued_at, id)."""

from __future__ import annotations

import json
import sqlite3

from noveltrad.core.clock import utc_now
from noveltrad.core.contracts import (
    DocumentId,
    JobId,
    PipelineSnapshot,
    ProjectId,
    SegmentId,
)
from noveltrad.core.exceptions import NotFoundError

from .models import JobRow

_COLUMNS = (
    "id, document_id, state, provider, model, snapshot_json, snapshot_hash, "
    "current_stage, current_segment_id, progress, last_message, control_request, "
    "control_requested_at, next_retry_at, queued_at, started_at, finished_at"
)


def _row_to_job(row: sqlite3.Row) -> JobRow:
    from noveltrad.core.contracts import JobState, PipelineStage

    return JobRow(
        id=row["id"],
        document_id=row["document_id"],
        state=JobState(row["state"]),
        provider=row["provider"],
        model=row["model"],
        snapshot_json=row["snapshot_json"],
        snapshot_hash=row["snapshot_hash"],
        current_stage=(
            PipelineStage(row["current_stage"]) if row["current_stage"] else None
        ),
        current_segment_id=row["current_segment_id"],
        progress=row["progress"],
        last_message=row["last_message"],
        control_request=row["control_request"],
        control_requested_at=row["control_requested_at"],
        next_retry_at=row["next_retry_at"],
        queued_at=row["queued_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def serialize_snapshot(snapshot: PipelineSnapshot) -> str:
    """Canonical JSON of all PipelineSnapshot fields except snapshot_hash."""
    provider = snapshot.provider
    provider_value = provider.value if hasattr(provider, "value") else str(provider)
    payload = {
        "provider": provider_value,
        "base_url": snapshot.base_url,
        "model": snapshot.model,
        "context_window_tokens": snapshot.context_window_tokens,
        "tokenizer_id": snapshot.tokenizer_id,
        "temperature": snapshot.temperature,
        "max_output_tokens": snapshot.max_output_tokens,
        "seed": snapshot.seed,
        "prompt_bundle_version": snapshot.prompt_bundle_version,
        "response_schema_version": snapshot.response_schema_version,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deserialize_snapshot(snapshot_json: str, snapshot_hash: str) -> PipelineSnapshot:
    from noveltrad.core.contracts import ProviderName

    payload = json.loads(snapshot_json)
    return PipelineSnapshot(
        provider=ProviderName(payload["provider"]),
        base_url=payload["base_url"],
        model=payload["model"],
        context_window_tokens=payload["context_window_tokens"],
        tokenizer_id=payload["tokenizer_id"],
        temperature=payload["temperature"],
        max_output_tokens=payload["max_output_tokens"],
        seed=payload["seed"],
        prompt_bundle_version=payload["prompt_bundle_version"],
        response_schema_version=payload["response_schema_version"],
        snapshot_hash=snapshot_hash,
    )


class JobRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(
        self,
        document_id: DocumentId,
        snapshot: PipelineSnapshot,
        state: str = "Waiting",
    ) -> JobRow:
        now = utc_now().isoformat()
        snapshot_json = serialize_snapshot(snapshot)
        provider_value = (
            snapshot.provider.value
            if hasattr(snapshot.provider, "value")
            else str(snapshot.provider)
        )
        cur = self._conn.execute(
            "INSERT INTO jobs (document_id, state, provider, model, snapshot_json, "
            "snapshot_hash, progress, queued_at) VALUES (?, ?, ?, ?, ?, ?, 0.0, ?)",
            (
                document_id,
                state,
                provider_value,
                snapshot.model,
                snapshot_json,
                snapshot.snapshot_hash,
                now,
            ),
        )
        return self.get(JobId(int(cur.lastrowid)))

    def get(self, job_id: JobId) -> JobRow:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE id=?", (job_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"job {job_id} not found")
        return _row_to_job(row)

    def list_by_project(self, project_id: ProjectId) -> list[JobRow]:
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE document_id IN "
            "(SELECT id FROM documents WHERE project_id=?) ORDER BY queued_at, id",
            (project_id,),
        ).fetchall()
        return [_row_to_job(r) for r in rows]

    def first_queued(self) -> JobRow | None:
        """Strict FIFO head: first Queued ordered by (queued_at, id)."""
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE state='Queued' "
            "ORDER BY queued_at, id LIMIT 1"
        ).fetchone()
        return _row_to_job(row) if row else None

    def active_job(self) -> JobRow | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE state IN ('Running','Retrying') LIMIT 1"
        ).fetchone()
        return _row_to_job(row) if row else None

    def open_job_for_document(self, document_id: DocumentId) -> JobRow | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE document_id=? AND state IN "
            "('Waiting','Queued','Running','Paused','Retrying','Failed') LIMIT 1",
            (document_id,),
        ).fetchone()
        return _row_to_job(row) if row else None

    def promote_next_waiting(self, project_id: ProjectId) -> JobRow | None:
        """Promote the first Waiting job of the project to Queued."""
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE document_id IN "
            "(SELECT id FROM documents WHERE project_id=?) AND state='Waiting' "
            "ORDER BY queued_at, id LIMIT 1",
            (project_id,),
        ).fetchone()
        if row is None:
            return None
        self._conn.execute("UPDATE jobs SET state='Queued' WHERE id=?", (row["id"],))
        return _row_to_job(row)

    def update_state(
        self,
        job_id: JobId,
        state: str,
        *,
        progress: float | None = None,
        current_stage: str | None = None,
        current_segment_id: SegmentId | None = None,
        message: str | None = None,
        next_retry_at: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
    ) -> JobRow:
        sets = ["state=?"]
        params: list[object] = [state]
        if progress is not None:
            sets.append("progress=?")
            params.append(progress)
        if current_stage is not None:
            sets.append("current_stage=?")
            params.append(current_stage)
        if current_segment_id is not None:
            sets.append("current_segment_id=?")
            params.append(current_segment_id)
        if message is not None:
            sets.append("last_message=?")
            params.append(message)
        if next_retry_at is not None:
            sets.append("next_retry_at=?")
            params.append(next_retry_at)
        if started_at is not None:
            sets.append("started_at=?")
            params.append(started_at)
        if finished_at is not None:
            sets.append("finished_at=?")
            params.append(finished_at)
        params.append(job_id)
        self._conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", params)
        return self.get(job_id)

    def request_pause(self, job_id: JobId) -> JobRow:
        now = utc_now().isoformat()
        self._conn.execute(
            "UPDATE jobs SET control_request='PAUSE', control_requested_at=? WHERE id=?",
            (now, job_id),
        )
        return self.get(job_id)

    def clear_pause_request(self, job_id: JobId) -> JobRow:
        self._conn.execute(
            "UPDATE jobs SET control_request=NULL, control_requested_at=NULL WHERE id=?",
            (job_id,),
        )
        return self.get(job_id)

    def set_retry(self, job_id: JobId, next_retry_at: str, attempt: int) -> None:
        self._conn.execute(
            "UPDATE jobs SET state='Retrying', next_retry_at=?, last_message=? WHERE id=?",
            (next_retry_at, f"retry {attempt} scheduled", job_id),
        )

    def recover_interrupted(self) -> list[JobRow]:
        """Place Running/Retrying jobs back to Queued (12.16), keeping keys."""
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE state IN ('Running','Retrying')"
        ).fetchall()
        for row in rows:
            self._conn.execute(
                "UPDATE jobs SET state='Queued' WHERE id=?", (row["id"],)
            )
        return [_row_to_job(r) for r in rows]

    def job_for_document(self, document_id: DocumentId) -> JobRow | None:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE document_id=? ORDER BY id DESC LIMIT 1",
            (document_id,),
        ).fetchone()
        return _row_to_job(row) if row else None

    def count_open(self, project_id: ProjectId) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM jobs WHERE document_id IN "
            "(SELECT id FROM documents WHERE project_id=?) AND state NOT IN "
            "('Completed')",
            (project_id,),
        ).fetchone()
        return int(row["c"])

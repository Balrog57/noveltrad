"""Job entities (SDD 7.18, 8.7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from noveltrad.core.contracts import (
    DocumentId,
    Job,
    JobId,
    JobState,
    PipelineSnapshot,
    PipelineStage,
    SegmentId,
)


@dataclass(frozen=True, slots=True)
class JobRow:
    id: JobId
    document_id: DocumentId
    state: JobState
    provider: str
    model: str
    snapshot_json: str
    snapshot_hash: str
    current_stage: PipelineStage | None
    current_segment_id: SegmentId | None
    progress: float
    last_message: str | None
    control_request: str | None
    control_requested_at: str | None
    next_retry_at: str | None
    queued_at: str
    started_at: str | None
    finished_at: str | None


def to_job(row: JobRow, snapshot: PipelineSnapshot) -> Job:
    return Job(
        id=row.id,
        document_id=row.document_id,
        state=row.state,
        progress=row.progress,
        current_stage=row.current_stage,
        current_segment_id=row.current_segment_id,
        snapshot=snapshot,
        next_retry_at=_parse(row.next_retry_at) if row.next_retry_at else None,
    )


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)

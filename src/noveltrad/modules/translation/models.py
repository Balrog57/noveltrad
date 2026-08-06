"""Translation entities (SDD 7.18, 8.6 segments)."""

from __future__ import annotations

from dataclasses import dataclass

from noveltrad.core.contracts import SegmentId, SegmentState


@dataclass(frozen=True, slots=True)
class SegmentRow:
    id: SegmentId
    chapter_id: int
    order_index: int
    source_start: int
    source_end: int
    source_hash: str
    state: SegmentState
    checkpoint_path: str | None
    checkpoint_hash: str | None
    retry_count: int
    last_error: str | None
    updated_at: str

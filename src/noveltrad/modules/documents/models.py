"""Document entities (SDD 7.18, 8.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from noveltrad.core.contracts import (
    Chapter,
    ChapterId,
    Document,
    DocumentId,
    DocumentStatus,
    ProjectId,
    SegmentId,
    SegmentState,
)


@dataclass(frozen=True, slots=True)
class DocumentRow:
    id: DocumentId
    project_id: ProjectId
    display_name: str
    import_format: str
    order_index: int
    source_path: str
    source_hash: str
    translated_path: str | None
    translated_hash: str | None
    status: DocumentStatus
    progress: float
    word_count: int
    character_count: int
    detected_language: str | None
    last_error: str | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class ChapterRow:
    id: ChapterId
    document_id: DocumentId
    order_index: int
    title: str | None
    source_start: int
    source_end: int
    source_hash: str
    translated_start: int | None
    translated_end: int | None
    translated_hash: str | None


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


def to_document(row: DocumentRow) -> Document:
    return Document(
        id=row.id,
        project_id=row.project_id,
        display_name=row.display_name,
        order_index=row.order_index,
        status=row.status,
        progress=row.progress,
        word_count=row.word_count,
        character_count=row.character_count,
        detected_language=row.detected_language,
    )


def to_chapter(row: ChapterRow) -> Chapter:
    return Chapter(
        id=row.id,
        document_id=row.document_id,
        order_index=row.order_index,
        title=row.title,
    )


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)

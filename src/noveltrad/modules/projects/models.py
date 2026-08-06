"""Project entities (SDD 7.18)."""

from __future__ import annotations

from dataclasses import dataclass

from noveltrad.core.contracts import LanguageCode, Project, ProjectId, ProjectStatus


@dataclass(frozen=True, slots=True)
class ProjectRow:
    """Full persisted project row including notice timestamps."""

    id: ProjectId
    name: str
    source_language: LanguageCode | str | None
    target_language: LanguageCode
    status: ProjectStatus
    created_at: str
    updated_at: str
    completion_notice_claimed_at: str | None
    completion_notice_acknowledged_at: str | None


def to_contract(row: ProjectRow) -> Project:
    """Map the persisted row onto the public Project contract."""
    return Project(
        id=row.id,
        name=row.name,
        source_language=row.source_language,  # type: ignore[arg-type]
        target_language=row.target_language,
        status=row.status,
        created_at=_parse(row.created_at),
        updated_at=_parse(row.updated_at),
    )


def _parse(value: str):
    from datetime import UTC, datetime

    return datetime.fromisoformat(value).astimezone(UTC)

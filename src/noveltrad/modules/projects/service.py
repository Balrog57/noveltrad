"""ProjectService (SDD 5.8, 9.2, 9.13).

Creates, renames, validates, deletes and claims the terminal notice of a
work. A project represents exactly one work; target language is immutable
while a translation is active.
"""

from __future__ import annotations

import sqlite3

from noveltrad.core.contracts import (
    LanguageCode,
    Project,
    ProjectId,
    ProjectStatus,
    ValidationReport,
)
from noveltrad.core.exceptions import (
    LockedError,
    ValidationError,
)
from noveltrad.core.languages import is_valid_target
from noveltrad.core.logging import LogContext, LogService
from noveltrad.core.transactions import UnitOfWork

from .models import to_contract
from .repository import ProjectRepository


class ProjectService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        repository: ProjectRepository,
        logs: LogService,
        data_dir=None,
    ) -> None:
        self._conn = conn
        self._repo = repository
        self._logs = logs
        self._data_dir = data_dir

    # -- queries ----------------------------------------------------------

    def get(self, project_id: ProjectId) -> Project:
        return to_contract(self._repo.get_by_id(project_id))

    def list(self, query: str | None = None) -> tuple[Project, ...]:
        return tuple(to_contract(row) for row in self._repo.list_all(query))

    # -- mutations --------------------------------------------------------

    def create(self, name: str, target_language: LanguageCode) -> Project:
        if not name or not name.strip():
            raise ValidationError("project name must not be empty")
        if len(name) > 200:
            raise ValidationError("project name must not exceed 200 characters")
        if not is_valid_target(target_language):
            raise ValidationError(f"invalid target language: {target_language}")
        with UnitOfWork(self._conn):
            row = self._repo.insert(name.strip(), target_language)
            self._logs.record(
                "INFO",
                "project.create",
                "project created",
                _ctx(row.id),
                fields=(("target", target_language),),
            )
        return to_contract(row)

    def rename(self, project_id: ProjectId, name: str) -> Project:
        if not name or not name.strip():
            raise ValidationError("project name must not be empty")
        if len(name) > 200:
            raise ValidationError("project name must not exceed 200 characters")
        row = self._repo.get_by_id(project_id)
        if row.status in (ProjectStatus.RUNNING, ProjectStatus.PAUSED):
            raise LockedError("cannot rename a project during an active translation")
        with UnitOfWork(self._conn):
            updated = self._repo.update_name(project_id, name.strip())
            self._logs.record(
                "INFO",
                "project.rename",
                "project renamed",
                _ctx(project_id),
            )
        return to_contract(updated)

    def validate(self, project_id: ProjectId) -> ValidationReport:
        """Validate the project before launch (SDD 9.6, EF-007)."""
        row = self._repo.get_by_id(project_id)
        errors: list[str] = []
        messages: list[str] = []
        if self._repo.count_documents(project_id) == 0:
            errors.append("NO_DOCUMENTS")
            messages.append("the project contains no documents")
        for document in self._document_rows(project_id):
            if document["detected_language"] is None or document["detected_language"] == "und":
                errors.append("SOURCE_LANGUAGE_UNDETERMINED")
                messages.append(
                    f"document {document['display_name']}: source language undetermined"
                )
                break
        if row.status == ProjectStatus.RUNNING:
            errors.append("ALREADY_RUNNING")
            messages.append("a translation is already active")
        valid = not errors
        self._logs.record(
            "INFO" if valid else "WARNING",
            "project.validate",
            "project validation",
            _ctx(project_id),
            error_code=errors[0] if errors else None,
        )
        return ValidationReport(
            valid=valid,
            error_codes=tuple(errors),
            safe_messages=tuple(messages),
        )

    def delete(self, project_id: ProjectId, confirmation: str) -> None:
        row = self._repo.get_by_id(project_id)
        if confirmation != f"DELETE_PROJECT {project_id}":
            raise ValidationError("confirmation mismatch: expected DELETE_PROJECT <project_id>")
        if row.status in (ProjectStatus.RUNNING, ProjectStatus.PAUSED):
            raise LockedError("pause the translation before deleting the project")
        with UnitOfWork(self._conn):
            if self._data_dir is not None:
                from shutil import rmtree

                from noveltrad.core.paths import project_dir

                rmtree(project_dir(self._data_dir, project_id), ignore_errors=True)
            self._repo.delete(project_id)
        # Logged after commit; the cascade removed project-scoped rows, so the
        # project_id travels in safe fields instead of the FK column.
        from noveltrad.core.logging import new_correlation_id

        self._logs.record(
            "INFO",
            "project.delete",
            "project deleted",
            LogContext(correlation_id=new_correlation_id()),
            fields=(("project_id", project_id),),
        )

    # -- terminal notice (13.5) -------------------------------------------

    def claim_completion_notice(self, project_id: ProjectId) -> bool:
        row = self._repo.get_by_id(project_id)
        if row.status != ProjectStatus.COMPLETED:
            return False
        with UnitOfWork(self._conn):
            claimed = self._repo.claim_completion_notice(project_id)
            if claimed:
                self._logs.record(
                    "INFO",
                    "project.status",
                    "completion notice claimed",
                    _ctx(project_id),
                )
            return claimed

    def acknowledge_completion_notice(self, project_id: ProjectId) -> None:
        self._repo.get_by_id(project_id)
        with UnitOfWork(self._conn):
            self._repo.acknowledge_completion_notice(project_id)

    # -- helpers ----------------------------------------------------------

    def _document_rows(self, project_id: ProjectId):
        return self._conn.execute(
            "SELECT display_name, detected_language FROM documents WHERE project_id=? "
            "ORDER BY order_index",
            (project_id,),
        ).fetchall()


def _ctx(project_id: ProjectId) -> LogContext:
    from noveltrad.core.logging import new_correlation_id

    return LogContext(correlation_id=new_correlation_id(), project_id=project_id)

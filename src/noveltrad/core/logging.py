"""Structured correlated logging (SDD 16.9).

Every major event produces a UTC log row with a correlation_id, stable
event name, level, optional identifiers and safe flat scalar fields.
Prompts, responses, auth headers, URLs containing identifiers and raw
user-supplied paths are forbidden from logs.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
import uuid
from datetime import UTC, datetime

from .clock import utc_now
from .contracts import CorrelationId, LogContext, LogEntry, LogLevel, SafeFields
from .exceptions import StorageError, ValidationError
from .security import safe_scalars

_EVENTS = {
    "app.start",
    "app.stop",
    "auth.success",
    "auth.failure",
    "project.create",
    "project.rename",
    "project.delete",
    "project.validate",
    "project.status",
    "document.import",
    "document.convert",
    "document.reorder",
    "document.delete",
    "document.edit",
    "document.replace",
    "document.reset",
    "job.enqueue",
    "job.take",
    "job.pause",
    "job.resume",
    "job.retry",
    "job.completed",
    "job.failed",
    "segment.validated",
    "pipeline.stage",
    "export.generate",
    "export.download",
    "export.expired",
    "settings.update",
    "settings.validate",
    "worker.heartbeat",
    "worker.stop",
    "system.error",
    "system.cleanup",
    "system.recovery",
}


def new_correlation_id() -> CorrelationId:
    return CorrelationId(str(uuid.uuid4()))


def _parse_created_at(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError:
        return utc_now()


class LogService:
    """Business log service persisting safe correlated events (SDD 16.13)."""

    def __init__(self, conn: sqlite3.Connection, logger: logging.Logger | None = None) -> None:
        self._conn = conn
        self._logger = logger or logging.getLogger("noveltrad")

    def record(
        self,
        level: LogLevel,
        event: str,
        safe_message: str,
        context: LogContext,
        *,
        error_code: str | None = None,
        fields: SafeFields = (),
    ) -> None:
        if event not in _EVENTS:
            raise ValidationError(f"unknown log event: {event}")
        if level not in LogLevel:
            raise ValidationError(f"invalid log level: {level}")
        try:
            details = json.dumps(dict(fields)) if fields else None
            self._conn.execute(
                "INSERT INTO logs (created_at, level, event, project_id, document_id, "
                "job_id, correlation_id, error_code, message, details_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    utc_now().isoformat(),
                    str(level),
                    event,
                    context.project_id,
                    context.document_id,
                    context.job_id,
                    context.correlation_id,
                    error_code,
                    safe_message[:4096],
                    details,
                ),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise StorageError(f"cannot persist log entry: {exc}") from exc
        getattr(self._logger, str(level).lower(), self._logger.info)(
            "%s: %s", event, safe_message
        )

    def query(
        self,
        *,
        level: LogLevel | None = None,
        project_id=None,
        correlation_id: CorrelationId | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[LogEntry, ...]:
        if limit < 0 or offset < 0:
            raise ValidationError("limit and offset must be non-negative")
        clauses: list[str] = []
        params: list[object] = []
        if level is not None:
            clauses.append("level = ?")
            params.append(str(level))
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if correlation_id is not None:
            clauses.append("correlation_id = ?")
            params.append(correlation_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.extend([limit, offset])
        try:
            rows = self._conn.execute(
                f"SELECT * FROM logs{where} ORDER BY id DESC LIMIT ? OFFSET ?", params
            ).fetchall()
        except sqlite3.Error as exc:
            raise StorageError(f"cannot query logs: {exc}") from exc
        entries: list[LogEntry] = []
        for row in rows:
            fields: SafeFields = ()
            if row["details_json"]:
                try:
                    raw = json.loads(row["details_json"])
                    fields = safe_scalars(raw)
                except (ValueError, TypeError, json.JSONDecodeError):
                    fields = ()
            entries.append(
                LogEntry(
                    created_at=_parse_created_at(row["created_at"]),
                    level=LogLevel(row["level"]),
                    event=row["event"],
                    correlation_id=CorrelationId(row["correlation_id"]),
                    error_code=row["error_code"],
                    safe_message=row["message"],
                    project_id=row["project_id"],
                    document_id=row["document_id"],
                    job_id=row["job_id"],
                    fields=fields,
                )
            )
        return tuple(entries)


def setup_logger(level: str) -> logging.Logger:
    """Configure the root NovelTrad logger to stderr."""
    logger = logging.getLogger("noveltrad")
    logger.setLevel(getattr(logging, level))
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger

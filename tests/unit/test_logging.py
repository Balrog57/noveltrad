"""Unit tests for core.logging (SDD 16.9)."""

from __future__ import annotations

import pytest

from noveltrad.core.contracts import LogContext, LogLevel
from noveltrad.core.exceptions import ValidationError
from noveltrad.core.logging import LogService, new_correlation_id


def test_record_and_query(conn):
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
        "VALUES ('book', 'fr', 'Draft', ?, ?)",
        (now, now),
    )
    conn.commit()
    project_id = conn.execute("SELECT id FROM projects").fetchone()[0]
    service = LogService(conn)
    correlation = new_correlation_id()
    service.record(
        LogLevel.INFO,
        "project.create",
        "created project",
        LogContext(correlation_id=correlation, project_id=project_id),
        fields=(("size", 3), ("ok", True)),
    )
    entries = service.query()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.event == "project.create"
    assert entry.project_id == project_id
    assert entry.correlation_id == correlation
    assert dict(entry.fields)["size"] == 3


def test_filter_by_level(conn):
    service = LogService(conn)
    correlation = new_correlation_id()
    service.record(LogLevel.ERROR, "system.error", "boom", LogContext(correlation_id=correlation))
    service.record(
        LogLevel.INFO,
        "app.start",
        "started",
        LogContext(correlation_id=correlation),
    )
    errors = service.query(level=LogLevel.ERROR)
    assert len(errors) == 1
    assert errors[0].level == LogLevel.ERROR


def test_unknown_event_rejected(conn):
    service = LogService(conn)
    with pytest.raises(ValidationError):
        service.record(
            LogLevel.INFO,
            "not.a.real.event",
            "x",
            LogContext(correlation_id=new_correlation_id()),
        )


def test_secret_never_logged(conn):
    service = LogService(conn)
    service.record(
        LogLevel.INFO,
        "auth.failure",
        "authentication failed",
        LogContext(correlation_id=new_correlation_id()),
        error_code="AUTH_FAILED",
        fields=(("attempt", 2),),
    )
    rows = conn.execute("SELECT message, details_json FROM logs").fetchall()
    assert all("secret" not in str(row[0]).lower() for row in rows)


def test_correlation_filter(conn):
    service = LogService(conn)
    c1, c2 = new_correlation_id(), new_correlation_id()
    service.record(LogLevel.INFO, "app.start", "a", LogContext(correlation_id=c1))
    service.record(LogLevel.INFO, "app.start", "b", LogContext(correlation_id=c2))
    assert len(service.query(correlation_id=c1)) == 1

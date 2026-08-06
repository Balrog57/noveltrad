"""Unit tests for JobService FIFO and state machine (SDD 12, 12.15)."""

from __future__ import annotations

import sqlite3

import pytest

from noveltrad.core.contracts import (
    JobState,
    PipelineSnapshot,
    ProjectStatus,
)
from noveltrad.core.exceptions import ConflictError
from noveltrad.core.logging import LogService
from noveltrad.modules.jobs.repository import JobRepository
from noveltrad.modules.jobs.service import JobService


@pytest.fixture
def job_service(conn: sqlite3.Connection) -> JobService:
    logs = LogService(conn)
    repo = JobRepository(conn)
    return JobService(conn, repo, logs)


def _snapshot() -> PipelineSnapshot:
    return PipelineSnapshot(
        provider="ollama",
        base_url="http://localhost:11434",
        model="qwen2.5",
        context_window_tokens=8192,
        tokenizer_id="utf8-bytes-v1",
        temperature=0.2,
        max_output_tokens=2048,
        seed=None,
        prompt_bundle_version="v1",
        response_schema_version="v1",
        snapshot_hash="abc123",
    )


def _project_with_docs(conn: sqlite3.Connection, count: int = 2) -> int:
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
        "VALUES ('book', 'fr', 'Ready', ?, ?)",
        (now, now),
    )
    project_id = int(conn.execute("SELECT id FROM projects").fetchone()[0])
    for index in range(count):
        conn.execute(
            "INSERT INTO documents (project_id, display_name, import_format, order_index, "
            "source_path, source_hash, status, detected_language, updated_at) "
            "VALUES (?, ?, 'txt', ?, ?, 'h', 'ToTranslate', 'en', ?)",
            (project_id, f"doc{index}", index, f"p{index}", now),
        )
    conn.commit()
    return project_id


def test_enqueue_creates_fifo(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 3)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    assert len(jobs) == 3
    assert jobs[0].state == JobState.QUEUED
    assert jobs[1].state == JobState.WAITING
    assert jobs[2].state == JobState.WAITING
    status = conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()[0]
    assert status == ProjectStatus.RUNNING.value


def test_take_next_single_active(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 3)
    job_service.enqueue_project(project_id, _snapshot())
    taken = job_service.take_next()
    assert taken is not None
    assert taken.state == JobState.RUNNING
    assert job_service.take_next() is None  # one active job only
    row = conn.execute("SELECT COUNT(*) FROM jobs WHERE state='Running'").fetchone()[0]
    assert row == 1


def test_mark_completed_promotes_next(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 3)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    job_service.mark_completed(jobs[0].id)
    remaining = conn.execute("SELECT state FROM jobs WHERE id=?", (jobs[1].id,)).fetchone()[0]
    assert remaining == "Queued"
    assert (
        conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()[0]
        == "Running"
    )


def test_mark_completed_finishes_project(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 2)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    job_service.mark_completed(jobs[0].id)
    job_service.mark_completed(jobs[1].id)
    assert (
        conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()[0]
        == "Completed"
    )
    statuses = [
        tuple(row)
        for row in conn.execute("SELECT status FROM documents WHERE project_id=?", (project_id,))
    ]
    assert statuses == [("Completed",), ("Completed",)]


def test_request_pause_then_apply(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 2)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    job_service.request_pause(project_id)
    row = conn.execute("SELECT control_request FROM jobs WHERE id=?", (jobs[0].id,)).fetchone()[0]
    assert row == "PAUSE"
    job_service.apply_pause(jobs[0].id)
    assert (
        conn.execute("SELECT state FROM jobs WHERE id=?", (jobs[0].id,)).fetchone()[0] == "Paused"
    )
    assert (
        conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()[0]
        == "Paused"
    )


def test_take_next_respects_pause_request(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 1)
    job_service.enqueue_project(project_id, _snapshot())
    job_service.request_pause(project_id)
    taken = job_service.take_next()
    assert taken is not None
    assert taken.state == JobState.PAUSED


def test_resume_paused(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 1)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    job_service.apply_pause(jobs[0].id)
    resumed = job_service.resume(jobs[0].id)
    assert resumed.state == JobState.QUEUED


def test_mark_failed(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 2)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    job_service.mark_failed(jobs[0].id, "PROVIDER_ERROR")
    assert (
        conn.execute("SELECT state FROM jobs WHERE id=?", (jobs[0].id,)).fetchone()[0] == "Failed"
    )
    assert (
        conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()[0]
        == "Failed"
    )
    # no promotion after failure
    assert (
        conn.execute("SELECT state FROM jobs WHERE id=?", (jobs[1].id,)).fetchone()[0] == "Waiting"
    )


def test_resume_failed(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 1)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    job_service.mark_failed(jobs[0].id, "X")
    resumed = job_service.resume(jobs[0].id)
    assert resumed.state == JobState.QUEUED
    assert (
        conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()[0]
        == "Running"
    )


def test_recover_interrupted(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 1)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    conn.execute("UPDATE jobs SET state='Running' WHERE id=?", (jobs[0].id,))
    conn.commit()
    job_service.recover_interrupted()
    assert (
        conn.execute("SELECT state FROM jobs WHERE id=?", (jobs[0].id,)).fetchone()[0] == "Queued"
    )


def test_enqueue_rejects_running_project(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 1)
    job_service.enqueue_project(project_id, _snapshot())
    with pytest.raises(ConflictError):
        job_service.enqueue_project(project_id, _snapshot())


def test_get_progress(job_service: JobService, conn: sqlite3.Connection):
    project_id = _project_with_docs(conn, 2)
    jobs = job_service.enqueue_project(project_id, _snapshot())
    job_service.mark_completed(jobs[0].id)
    progress = job_service.get_progress(project_id)
    assert progress.project_status == ProjectStatus.RUNNING
    assert progress.completed_documents == 1
    assert progress.total_documents == 2

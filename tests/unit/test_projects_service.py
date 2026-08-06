"""Unit tests for ProjectService (SDD 9.2, 9.6, 9.8, 9.13, 13.5)."""

from __future__ import annotations

import sqlite3

import pytest

from noveltrad.core.contracts import LanguageCode, ProjectStatus
from noveltrad.core.exceptions import LockedError, ValidationError
from noveltrad.core.logging import LogService
from noveltrad.modules.projects.repository import ProjectRepository
from noveltrad.modules.projects.service import ProjectService


@pytest.fixture
def project_service(conn: sqlite3.Connection, data_dir):
    logs = LogService(conn)
    repo = ProjectRepository(conn)
    return ProjectService(conn, repo, logs, data_dir=data_dir)


def test_create_draft(project_service: ProjectService):
    project = project_service.create("Les Misérables", LanguageCode("fr"))
    assert project.status == ProjectStatus.DRAFT
    assert project.target_language == "fr"
    assert project.name == "Les Misérables"


def test_get_after_create_status_is_enum(project_service: ProjectService):
    """Regression: the project view crashed on str.status.value (SDD 13.5)."""
    project = project_service.create("Book", LanguageCode("fr"))
    reloaded = project_service.get(project.id)
    assert reloaded.status == ProjectStatus.DRAFT
    assert reloaded.status.value == "Draft"


def test_create_rejects_bad_language(project_service: ProjectService):
    with pytest.raises(ValidationError):
        project_service.create("x", LanguageCode("und"))
    with pytest.raises(ValidationError):
        project_service.create("x", LanguageCode("mul"))
    with pytest.raises(ValidationError):
        project_service.create("x", LanguageCode("zz"))


def test_create_rejects_empty_name(project_service: ProjectService):
    with pytest.raises(ValidationError):
        project_service.create("  ", LanguageCode("fr"))


def test_list_and_get(project_service: ProjectService):
    first = project_service.create("A", LanguageCode("fr"))
    second = project_service.create("B", LanguageCode("en"))
    listed = project_service.list()
    assert len(listed) == 2
    assert project_service.get(first.id) == first
    assert project_service.get(second.id).name == "B"


def test_list_with_query(project_service: ProjectService):
    project_service.create("One", LanguageCode("fr"))
    project_service.create("Two", LanguageCode("en"))
    assert len(project_service.list("One")) == 1
    assert len(project_service.list("o")) == 2


def test_rename(project_service: ProjectService):
    project = project_service.create("Old", LanguageCode("fr"))
    renamed = project_service.rename(project.id, "New")
    assert renamed.name == "New"


def test_rename_blocked_during_translation(
    conn: sqlite3.Connection, project_service: ProjectService
):
    project = project_service.create("X", LanguageCode("fr"))
    conn.execute("UPDATE projects SET status='Running' WHERE id=?", (project.id,))
    conn.commit()
    with pytest.raises(LockedError):
        project_service.rename(project.id, "Y")


def test_validate_empty_project(project_service: ProjectService):
    project = project_service.create("X", LanguageCode("fr"))
    report = project_service.validate(project.id)
    assert not report.valid
    assert "NO_DOCUMENTS" in report.error_codes


def test_validate_with_undetermined_language(
    conn: sqlite3.Connection, project_service: ProjectService
):
    project = project_service.create("X", LanguageCode("fr"))
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO documents (project_id, display_name, import_format, order_index, "
        "source_path, source_hash, status, updated_at) VALUES (?, 'd', 'txt', 0, "
        "'p', 'h', 'ToTranslate', ?)",
        (project.id, now),
    )
    conn.commit()
    report = project_service.validate(project.id)
    assert not report.valid
    assert "SOURCE_LANGUAGE_UNDETERMINED" in report.error_codes


def test_validate_ok(conn: sqlite3.Connection, project_service: ProjectService):
    project = project_service.create("X", LanguageCode("fr"))
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO documents (project_id, display_name, import_format, order_index, "
        "source_path, source_hash, status, detected_language, updated_at) "
        "VALUES (?, 'd', 'txt', 0, 'p', 'h', 'ToTranslate', 'en', ?)",
        (project.id, now),
    )
    conn.commit()
    report = project_service.validate(project.id)
    assert report.valid
    assert report.error_codes == ()


def test_delete_requires_confirmation(project_service: ProjectService):
    project = project_service.create("X", LanguageCode("fr"))
    with pytest.raises(ValidationError):
        project_service.delete(project.id, "wrong")
    project_service.delete(project.id, f"DELETE_PROJECT {project.id}")
    assert project_service.list() == ()


def test_delete_blocked_when_running(conn: sqlite3.Connection, project_service: ProjectService):
    project = project_service.create("X", LanguageCode("fr"))
    conn.execute("UPDATE projects SET status='Running' WHERE id=?", (project.id,))
    conn.commit()
    with pytest.raises(LockedError):
        project_service.delete(project.id, f"DELETE_PROJECT {project.id}")


def test_delete_removes_project_dir(project_service: ProjectService, data_dir):
    project = project_service.create("X", LanguageCode("fr"))
    from noveltrad.core.paths import project_dir

    folder = project_dir(data_dir, project.id)
    folder.mkdir(parents=True)
    (folder / "source.md").write_text("x")
    project_service.delete(project.id, f"DELETE_PROJECT {project.id}")
    assert not folder.exists()


def test_completion_notice_claim_once(conn: sqlite3.Connection, project_service: ProjectService):
    project = project_service.create("X", LanguageCode("fr"))
    conn.execute("UPDATE projects SET status='Completed' WHERE id=?", (project.id,))
    conn.commit()
    assert project_service.claim_completion_notice(project.id) is True
    assert project_service.claim_completion_notice(project.id) is False


def test_completion_notice_only_when_completed(project_service: ProjectService):
    project = project_service.create("X", LanguageCode("fr"))
    assert project_service.claim_completion_notice(project.id) is False


def test_acknowledge_completion_notice(conn: sqlite3.Connection, project_service: ProjectService):
    project = project_service.create("X", LanguageCode("fr"))
    conn.execute("UPDATE projects SET status='Completed' WHERE id=?", (project.id,))
    conn.commit()
    project_service.acknowledge_completion_notice(project.id)
    row = conn.execute(
        "SELECT completion_notice_acknowledged_at FROM projects WHERE id=?", (project.id,)
    ).fetchone()
    assert row[0] is not None

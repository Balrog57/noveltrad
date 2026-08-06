"""Unit tests for export (SDD 15)."""

from __future__ import annotations

import io
import sqlite3
import zipfile
from pathlib import Path

import pytest

from noveltrad.core.contracts import ProjectId
from noveltrad.core.exceptions import ConflictError, IntegrityError
from noveltrad.core.logging import LogService
from noveltrad.modules.export.archive import build_archive, slugify
from noveltrad.modules.export.service import ExportService


def test_slugify_basic():
    assert slugify("Les Misérables", ProjectId(3)) == "les-miserables"
    assert slugify("!!!!", ProjectId(7)) == "noveltrad-7"
    assert slugify("A  B", ProjectId(1)) == "a-b"


def test_slugify_truncates_to_80():
    slug = slugify("x" * 200, ProjectId(1))
    assert len(slug) <= 80


def test_build_archive_deterministic(tmp_path: Path):
    buffer = build_archive(
        "artifact1",
        "book.md",
        b"# Title\n",
        [("images/bbb.webp", b"bbb"), ("images/aaa.webp", b"aaa")],
    )
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        names = archive.namelist()
        assert names == ["book.md", "images/aaa.webp", "images/bbb.webp"]
        info = archive.getinfo("images/aaa.webp")
        assert info.date_time == (1980, 1, 1, 0, 0, 0)


def test_build_archive_rejects_unsafe_name():
    with pytest.raises(IntegrityError):
        build_archive("a", "../evil.md", b"x", [])


@pytest.fixture
def export_service(conn: sqlite3.Connection, data_dir: Path) -> ExportService:
    logs = LogService(conn)
    return ExportService(conn, logs, data_dir)


def _completed_project(conn: sqlite3.Connection, data_dir: Path) -> tuple[int, Path]:
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
        "VALUES ('book', 'fr', 'Completed', ?, ?)",
        (now, now),
    )
    project_id = int(conn.execute("SELECT id FROM projects").fetchone()[0])
    doc_dir = data_dir / "projects" / str(project_id) / "1"
    doc_dir.mkdir(parents=True)
    (doc_dir / "translated.md").write_text("Translated content.", encoding="utf-8")
    conn.execute(
        "INSERT INTO documents (project_id, display_name, import_format, order_index, "
        "source_path, source_hash, translated_path, translated_hash, status, updated_at) "
        "VALUES (?, 'doc', 'txt', 0, 'p', 'h', ?, 'h2', 'Completed', ?)",
        (project_id, f"projects/{project_id}/1/translated.md", now),
    )
    conn.commit()
    return project_id, doc_dir


def test_generate_zip(export_service: ExportService, conn: sqlite3.Connection, data_dir: Path):
    project_id, _ = _completed_project(conn, data_dir)
    artifact = export_service.generate(project_id)
    assert artifact.media_type == "application/zip"
    assert artifact.download_name == "book.md"
    path = export_service.open(artifact.id)
    with zipfile.ZipFile(path) as archive:
        assert archive.read("book.md").decode("utf-8") == "Translated content.\n"
    export_service.cleanup(artifact.id)


def test_generate_blocked_when_not_completed(
    export_service: ExportService, conn: sqlite3.Connection
):
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
        "VALUES ('x', 'fr', 'Draft', ?, ?)",
        (now, now),
    )
    conn.commit()
    project_id = int(conn.execute("SELECT id FROM projects").fetchone()[0])
    with pytest.raises(ConflictError):
        export_service.generate(project_id)


def test_open_unknown_artifact(export_service: ExportService):
    from noveltrad.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        export_service.open("unknown-id")

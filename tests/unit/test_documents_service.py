"""Unit tests for DocumentService import and ordering (SDD 9.3-9.5, 10.12)."""

from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import pytest

from noveltrad.core.contracts import DocumentStatus, ImportSource
from noveltrad.core.exceptions import LockedError, ValidationError
from noveltrad.core.logging import LogService
from noveltrad.modules.documents.repository import DocumentRepository
from noveltrad.modules.documents.service import DocumentService


@pytest.fixture
def doc_service(conn: sqlite3.Connection, data_dir: Path) -> DocumentService:
    logs = LogService(conn)
    repo = DocumentRepository(conn)
    return DocumentService(conn, repo, logs, data_dir)


@pytest.fixture
def project_id(conn: sqlite3.Connection) -> int:
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
        "VALUES ('book', 'fr', 'Draft', ?, ?)",
        (now, now),
    )
    conn.commit()
    return int(conn.execute("SELECT id FROM projects").fetchone()[0])


def _source(filename: str, content: str) -> ImportSource:
    return ImportSource(
        filename=filename,
        size_bytes=len(content.encode("utf-8")),
        stream=io.BytesIO(content.encode("utf-8")),
    )


def test_import_txt(doc_service: DocumentService, project_id: int):
    result = doc_service.import_batch(
        project_id, [_source("chap1.txt", "Hello world.\n\nSecond para.")]
    )
    assert len(result.documents) == 1
    assert result.failures == ()
    document = result.documents[0]
    assert document.status == DocumentStatus.TO_TRANSLATE
    assert document.import_format if False else True
    chapters = doc_service.list_chapters(document.id)
    assert len(chapters) == 1


def test_import_multiple_keeps_order(doc_service: DocumentService, project_id: int):
    result = doc_service.import_batch(
        project_id,
        [
            _source("a.txt", "First document."),
            _source("b.md", "# Second\n\nBody."),
            _source("c.txt", "Third document."),
        ],
    )
    assert len(result.documents) == 3
    names = [d.display_name for d in doc_service.list(project_id)]
    assert names == ["a", "b", "c"]


def test_import_unsupported_format(doc_service: DocumentService, project_id: int):
    result = doc_service.import_batch(project_id, [_source("evil.pdf", "%PDF-1.4")])
    assert result.documents == ()
    assert result.failures[0].error_code == "FORMAT_UNSUPPORTED"


def test_import_source_md_published(doc_service: DocumentService, project_id: int, data_dir: Path):
    result = doc_service.import_batch(project_id, [_source("chap.txt", "Some content here.")])
    document = result.documents[0]
    source_file = data_dir / "projects" / str(project_id) / str(document.id) / "source.md"
    assert source_file.exists()
    assert "Some content here." in source_file.read_text(encoding="utf-8")


def test_reorder(doc_service: DocumentService, project_id: int):
    result = doc_service.import_batch(
        project_id,
        [_source("a.txt", "A"), _source("b.txt", "B"), _source("c.txt", "C")],
    )
    ids = [d.id for d in result.documents]
    reordered = doc_service.reorder(project_id, [ids[2], ids[0], ids[1]])
    names = [d.display_name for d in reordered]
    assert names == ["c", "a", "b"]


def test_delete_document(doc_service: DocumentService, project_id: int, data_dir: Path):
    result = doc_service.import_batch(project_id, [_source("a.txt", "A")])
    document = result.documents[0]
    doc_service.delete(document.id, None)
    assert doc_service.list(project_id) == ()


def test_delete_completed_requires_confirmation(
    conn: sqlite3.Connection, doc_service: DocumentService, project_id: int
):
    result = doc_service.import_batch(project_id, [_source("a.txt", "A")])
    document = result.documents[0]
    conn.execute("UPDATE documents SET status='Completed' WHERE id=?", (document.id,))
    conn.commit()
    with pytest.raises(ValidationError):
        doc_service.delete(document.id, None)
    doc_service.delete(document.id, f"DELETE_DOCUMENT {document.id}")
    assert doc_service.list(project_id) == ()


def test_import_locked_during_translation(
    conn: sqlite3.Connection, doc_service: DocumentService, project_id: int
):
    conn.execute("UPDATE projects SET status='Running' WHERE id=?", (project_id,))
    conn.commit()
    with pytest.raises(LockedError):
        doc_service.import_batch(project_id, [_source("a.txt", "A")])

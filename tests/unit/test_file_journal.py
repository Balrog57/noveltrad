"""Unit tests for core.file_journal (SDD 8.13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from noveltrad.core.file_journal import FileJournal


def test_insert_and_phases(file_journal: FileJournal):
    op_id = file_journal.insert_prepared(
        "IMPORT_DOCUMENT",
        "projects/1/2/source.md",
        staged_path="tmp/import-5/lot.md",
        project_id=1,
        document_id=2,
        payload_hash="abc",
    )
    row = file_journal.pending()[0]
    assert row["phase"] == "PREPARED"
    file_journal.advance_to_db_committed(op_id)
    assert file_journal.pending("DB_COMMITTED")[0]["id"] == op_id
    file_journal.advance_to_published(op_id)
    file_journal.remove(op_id)
    assert file_journal.pending() == []


def test_invalid_operation_rejected(file_journal: FileJournal):
    from noveltrad.core.exceptions import StorageError

    with pytest.raises(StorageError):
        file_journal.insert_prepared("UNKNOWN", "projects/1/2/source.md")


def test_recover_finishes_db_committed(data_dir: Path, file_journal: FileJournal):
    staged = data_dir / "tmp" / "import-1"
    staged.mkdir(parents=True)
    payload = staged / "lot.md"
    payload.write_text("content")
    op_id = file_journal.insert_prepared(
        "IMPORT_DOCUMENT",
        "projects/1/2/source.md",
        staged_path="tmp/import-1/lot.md",
    )
    file_journal.advance_to_db_committed(op_id)
    messages = file_journal.recover()
    assert messages == []
    assert (data_dir / "projects" / "1" / "2" / "source.md").exists()
    assert file_journal.pending() == []


def test_recover_compensates_missing_staged(data_dir: Path, file_journal: FileJournal):
    removed: list[str] = []
    file_journal.insert_prepared(
        "IMPORT_DOCUMENT",
        "projects/1/2/source.md",
        staged_path="tmp/missing/lot.md",
    )
    file_journal.advance_to_db_committed(1)
    messages = file_journal.recover(remove_business_row=lambda op, pid, did: removed.append(op))
    assert any("compensated" in m for m in messages)
    assert removed == ["IMPORT_DOCUMENT"]
    assert file_journal.pending() == []


def test_recover_restores_prepared_delete(data_dir: Path, file_journal: FileJournal):
    target = data_dir / "projects" / "1" / "2" / "translated.md"
    target.parent.mkdir(parents=True)
    target.write_text("keep me")
    trash = data_dir / "trash"
    trash.mkdir(exist_ok=True)
    moved = trash / "op-7"
    from noveltrad.core.atomic_files import rename_atomic

    rename_atomic(target, moved)
    file_journal.insert_prepared(
        "DELETE_DOCUMENT",
        "projects/1/2/translated.md",
        staged_path="trash/op-7",
    )
    restored: list[tuple[str, str]] = []

    def restore(staged: str, destination: str) -> None:
        restored.append((staged, destination))
        from noveltrad.core.atomic_files import rename_atomic
        from noveltrad.core.paths import resolve

        rename_atomic(resolve(data_dir, staged), resolve(data_dir, destination))

    file_journal.recover(restore_target=restore)
    assert restored == [("trash/op-7", "projects/1/2/translated.md")]
    assert target.exists()
    assert file_journal.pending() == []

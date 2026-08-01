"""Foreign-key enforcement and orphan purge for the jobs database.

SQLite ignores `ON DELETE CASCADE` unless `PRAGMA foreign_keys` is on, and that
pragma is scoped per connection. These tests pin the pragma, the cascade it
enables, the explicit defence-in-depth deletes, and the one-off purge that
reclaims chunk rows orphaned before enforcement existed.
"""

import sqlite3

import pytest

from src.core.adapters.translate_file import _ensure_checkpoint_job
from src.persistence.checkpoint_manager import CheckpointManager
from src.persistence.database import Database


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "jobs.db")


@pytest.fixture
def db(db_path):
    database = Database(db_path)
    yield database
    database.close()


def _count_chunks(database, translation_id):
    conn = database._get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM checkpoint_chunks WHERE translation_id = ?",
        (translation_id,),
    ).fetchone()
    return row[0]


def test_foreign_keys_pragma_is_enabled(db):
    assert db._get_connection().execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_delete_job_removes_its_chunks(db):
    assert db.create_job("t1", "txt", {}) is True
    assert db.save_chunk("t1", 0, "a", "b") is True

    assert db.delete_job("t1") is True

    assert _count_chunks(db, "t1") == 0


def test_cleanup_old_jobs_removes_chunks(db):
    assert db.create_job("old", "txt", {}) is True
    assert db.save_chunk("old", 0, "a", "b") is True
    assert db.save_chunk("old", 1, "c", "d") is True

    conn = db._get_connection()
    conn.execute(
        """
        UPDATE translation_jobs
        SET status = 'paused', created_at = datetime('now', '-60 days')
        WHERE translation_id = ?
        """,
        ("old",),
    )
    conn.commit()

    assert db.cleanup_old_jobs(max_age_days=30) == 1
    assert _count_chunks(db, "old") == 0


def test_cleanup_old_jobs_with_nothing_to_delete(db):
    """The IN (...) delete must not be built with zero placeholders."""
    assert db.create_job("fresh", "txt", {}) is True
    assert db.save_chunk("fresh", 0, "a", "b") is True

    assert db.cleanup_old_jobs(max_age_days=30) == 0
    assert _count_chunks(db, "fresh") == 1


def test_orphan_chunks_are_purged_on_init(db_path):
    Database(db_path).close()

    # Simulate a row orphaned by a delete performed while enforcement was off.
    raw = sqlite3.connect(db_path)
    raw.execute("PRAGMA foreign_keys=OFF")
    raw.execute(
        """
        INSERT INTO checkpoint_chunks
        (translation_id, chunk_index, original_text, translated_text, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("ghost", 0, "a", "b", "completed"),
    )
    raw.commit()
    raw.close()

    reopened = Database(db_path)
    try:
        assert _count_chunks(reopened, "ghost") == 0
    finally:
        reopened.close()


def test_orphan_purge_is_idempotent_on_a_clean_database(db_path, capsys):
    Database(db_path).close()
    capsys.readouterr()

    reopened = Database(db_path)
    try:
        assert "Reclaimed" not in capsys.readouterr().out
    finally:
        reopened.close()


def test_normal_write_order_still_succeeds(db_path):
    manager = CheckpointManager(db_path=db_path)
    try:
        assert manager.start_job("job", "txt", {}, None) is True
        assert manager.save_checkpoint(
            translation_id="job",
            chunk_index=0,
            original_text="a",
            translated_text="b",
            total_chunks=1,
            completed_chunks=1,
            failed_chunks=0,
        ) is True
        assert _count_chunks(manager.db, "job") == 1
    finally:
        manager.db.close()


def test_save_chunk_for_unknown_job_fails_cleanly(db):
    assert db.save_chunk("missing", 0, "a", "b") is False
    assert _count_chunks(db, "missing") == 0


class TestLegacyPipelineWriteOrder:
    """
    The legacy EPUB/DOCX pipelines save chunks without creating the job row.
    Under foreign-key enforcement that write is rejected, so translate_file()
    creates the row first. These tests pin that guard.
    """

    def test_missing_job_is_created_before_chunks_are_written(self, db_path):
        manager = CheckpointManager(db_path=db_path)
        try:
            _ensure_checkpoint_job(
                checkpoint_manager=manager,
                translation_id="cli-job",
                file_type="epub",
                config={"source_language": "English"},
                input_file_path=None,
            )

            assert manager.db.get_job("cli-job") is not None
            assert manager.db.save_chunk("cli-job", 0, "a", "b") is True
            assert _count_chunks(manager.db, "cli-job") == 1
        finally:
            manager.db.close()

    def test_existing_job_is_left_untouched(self, db_path):
        manager = CheckpointManager(db_path=db_path)
        try:
            manager.start_job("web-job", "epub", {"marker": "original"}, None)

            _ensure_checkpoint_job(
                checkpoint_manager=manager,
                translation_id="web-job",
                file_type="epub",
                config={"marker": "overwritten"},
                input_file_path=None,
            )

            job = manager.db.get_job("web-job")
            assert job["config"]["marker"] == "original"
        finally:
            manager.db.close()

    def test_no_checkpoint_manager_is_a_no_op(self):
        _ensure_checkpoint_job(None, "any", "epub", {}, None)
        _ensure_checkpoint_job(object(), None, "epub", {}, None)

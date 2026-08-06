"""Unit tests for core.database and migrations (SDD 8.3, 8.15)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from noveltrad.core.database import Database, initialize_schema
from noveltrad.core.exceptions import StorageError


def test_schema_tables_present(database: Database):
    conn = database.conn
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    expected = {
        "projects",
        "documents",
        "chapters",
        "segments",
        "jobs",
        "settings",
        "logs",
        "schema_migrations",
        "file_operations",
        "worker_runtime",
    }
    assert expected <= tables


def test_pragmas_applied(database: Database):
    conn = database.conn
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2  # FULL
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_initial_migration_version(database: Database):
    row = database.conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    assert row[0] == 1


def test_migration_idempotent(tmp_path: Path):
    db = initialize_schema(tmp_path / "a.sqlite")
    db.close()
    db2 = initialize_schema(tmp_path / "a.sqlite")
    version = db2.conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    assert version == 1
    db2.close()


def test_check_constraints_enforced(database: Database):
    conn = database.conn
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
            "VALUES ('x', 'fr', 'Invalid', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )


def test_foreign_key_cascade(database: Database):
    conn = database.conn
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
        "VALUES ('book', 'fr', 'Draft', ?, ?)",
        (now, now),
    )
    project_id = conn.execute("SELECT id FROM projects").fetchone()[0]
    conn.execute(
        "INSERT INTO documents (project_id, display_name, import_format, order_index, "
        "source_path, source_hash, status, updated_at) "
        "VALUES (?, 'doc', 'txt', 0, 'p', 'h', 'ToTranslate', ?)",
        (project_id, now),
    )
    conn.commit()
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0


def test_failed_migration_rolls_back(database: Database):
    """A failing migration must roll back fully and block startup."""
    conn = database.conn
    with pytest.raises(StorageError):
        database._apply_one(99, "CREATE TABLE tmp_ok (id INTEGER); BAD SQL;")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "tmp_ok" not in tables
    assert database.conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 1


def test_migration_backup_created(tmp_path: Path):
    db = Database(tmp_path / "b.sqlite", backups_dir=tmp_path / "backups")
    db.connect()
    db.migrate([(1, "CREATE TABLE t1 (id INTEGER PRIMARY KEY);")])
    db.migrate([(2, "ALTER TABLE t1 ADD COLUMN name TEXT;")])
    backups = list((tmp_path / "backups").glob("database-*.sqlite"))
    assert len(backups) == 1
    assert db.conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 2
    db.close()


def test_health(database: Database):
    assert database.health() is True

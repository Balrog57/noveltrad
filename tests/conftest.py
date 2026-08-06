"""Shared pytest fixtures for the NovelTrad test suite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from noveltrad.core.database import Database, initialize_schema
from noveltrad.core.file_journal import FileJournal


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite"


@pytest.fixture
def database(db_path: Path) -> Database:
    db = initialize_schema(db_path)
    yield db
    db.close()


@pytest.fixture
def conn(database: Database) -> sqlite3.Connection:
    return database.conn


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    base = tmp_path / "data"
    base.mkdir(parents=True, exist_ok=True)
    (base / "tmp").mkdir(exist_ok=True)
    (base / "trash").mkdir(exist_ok=True)
    return base


@pytest.fixture
def file_journal(conn: sqlite3.Connection, data_dir: Path) -> FileJournal:
    return FileJournal(conn, data_dir)

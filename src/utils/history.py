"""Local translation history (SQLite).

CDC F3.a: history of past translations, stored locally. Uses the stdlib sqlite3
module — no extra dependency. DB at ~/.noveltrad/history.db.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from src.utils.config import _config_dir

_SCHEMA = """
CREATE TABLE IF NOT EXISTS translations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  REAL NOT NULL,
    source_lang TEXT,
    target_lang TEXT,
    tone        TEXT,
    source_text TEXT NOT NULL,
    final_text  TEXT,
    fidelity    INTEGER,
    status      TEXT
);
"""


def _db_path() -> Path:
    return _config_dir() / "history.db"


def _connect() -> sqlite3.Connection:
    _config_dir().mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def add_entry(
    *,
    source_lang: str,
    target_lang: str,
    tone: str,
    source_text: str,
    final_text: str,
    fidelity: int | None = None,
    status: str | None = None,
) -> int:
    """Insert a finished translation into the history. Returns the new row id."""
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO translations
               (created_at, source_lang, target_lang, tone, source_text, final_text, fidelity, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (time.time(), source_lang, target_lang, tone, source_text, final_text, fidelity, status),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_entries(limit: int = 100) -> list[dict]:
    """Return recent history entries, most recent first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM translations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def clear() -> None:
    """Delete all history entries."""
    with _connect() as conn:
        conn.execute("DELETE FROM translations")
        conn.commit()

"""Settings persistence (SDD 8.8.1). API keys are stored encrypted."""

from __future__ import annotations

import sqlite3

from noveltrad.core.clock import utc_now
from noveltrad.core.exceptions import IntegrityError


class SettingsRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str) -> tuple[str | None, bool]:
        row = self._conn.execute(
            "SELECT value, is_secret FROM settings WHERE key=?", (key,)
        ).fetchone()
        if row is None:
            return None, False
        return row["value"], bool(row["is_secret"])

    def set(self, key: str, value: str | None, is_secret: bool = False) -> None:
        if is_secret and value is not None and not value.startswith("{"):
            raise IntegrityError("plaintext secret refused")
        self._conn.execute(
            "INSERT INTO settings (key, value, is_secret, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "is_secret=excluded.is_secret, updated_at=excluded.updated_at",
            (key, value, 1 if is_secret else 0, utc_now().isoformat()),
        )

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM settings WHERE key=?", (key,))

    def all(self) -> dict[str, tuple[str | None, bool]]:
        rows = self._conn.execute("SELECT key, value, is_secret FROM settings").fetchall()
        return {row["key"]: (row["value"], bool(row["is_secret"])) for row in rows}

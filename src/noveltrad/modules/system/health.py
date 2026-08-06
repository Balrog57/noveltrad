"""System diagnostics and container health (SDD 6.10, 16.7)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .service import SystemRepository

_HEARTBEAT_MAX_AGE = 15.0


class HealthService:
    """Read-only probes; never tests an AI provider (6.10)."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        data_dir: Path,
        repo: SystemRepository | None = None,
    ) -> None:
        self._conn = conn
        self._data_dir = data_dir
        self._repo = repo or SystemRepository(conn)

    def is_healthy(self) -> bool:
        """Healthy when SQLite answers SELECT 1, data dir is writable and
        the worker heartbeat is younger than 15 seconds."""
        try:
            row = self._conn.execute("SELECT 1").fetchone()
            if row is None:
                return False
        except sqlite3.Error:
            return False
        if not self._data_dir.exists():
            return False
        probe = self._data_dir / ".health-probe"
        try:
            probe.write_text("ok")
            probe.unlink()
        except OSError:
            return False
        runtime = self._repo.runtime()
        if not runtime["heartbeat_at"]:
            return False
        try:
            heartbeat = datetime.fromisoformat(runtime["heartbeat_at"]).astimezone(UTC)
        except ValueError:
            return False
        age = (datetime.now(UTC) - heartbeat).total_seconds()
        return age < _HEARTBEAT_MAX_AGE

    def snapshot(self) -> dict[str, str]:
        """Diagnostic summary without keys or content (16.13)."""
        runtime = self._repo.runtime()
        return {
            "worker_state": runtime["state"],
            "worker_started_at": runtime["started_at"],
            "healthy": "true" if self.is_healthy() else "false",
        }

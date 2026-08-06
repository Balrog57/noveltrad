"""System service (SDD 16.7): diagnostics summarized without secrets."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .health import HealthService
from .repository import SystemRepository


class SystemService:
    """Read-only diagnostics combining worker, SQLite and storage probes."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        data_dir: Path,
        repository: SystemRepository | None = None,
    ) -> None:
        self._conn = conn
        self._data_dir = data_dir
        self._repo = repository or SystemRepository(conn)

    def snapshot(self) -> dict[str, str]:
        runtime = self._repo.runtime()
        health = HealthService(self._conn, self._data_dir, self._repo)
        return {
            "worker_state": runtime["state"],
            "worker_started_at": runtime["started_at"],
            "healthy": "true" if health.is_healthy() else "false",
        }

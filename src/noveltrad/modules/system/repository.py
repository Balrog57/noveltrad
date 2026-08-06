"""System persistence: worker_runtime singleton (SDD 8.8.5, 6.10)."""

from __future__ import annotations

import sqlite3

from noveltrad.core.clock import utc_now


class SystemRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def ensure_runtime_row(self) -> None:
        now = utc_now().isoformat()
        self._conn.execute(
            "INSERT OR IGNORE INTO worker_runtime (id, state, heartbeat_at, started_at) "
            "VALUES (1, 'Starting', ?, ?)",
            (now, now),
        )
        self._conn.commit()

    def heartbeat(self, state: str) -> None:
        self._conn.execute(
            "UPDATE worker_runtime SET state=?, heartbeat_at=? WHERE id=1",
            (state, utc_now().isoformat()),
        )
        self._conn.commit()

    def runtime(self) -> dict[str, str]:
        row = self._conn.execute(
            "SELECT state, heartbeat_at, started_at FROM worker_runtime WHERE id=1"
        ).fetchone()
        if row is None:
            return {"state": "Starting", "heartbeat_at": "", "started_at": ""}
        return {
            "state": row["state"],
            "heartbeat_at": row["heartbeat_at"],
            "started_at": row["started_at"],
        }

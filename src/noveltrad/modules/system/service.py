"""System module: worker runtime health and cleanup (SDD 16.6, 16.7, 6.10)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from noveltrad.core.clock import utc_now
from noveltrad.core.logging import LogContext, LogService, new_correlation_id
from noveltrad.core.paths import tmp_dir, trash_dir

_HEARTBEAT_MAX_AGE = 15.0


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


class CleanupService:
    """Startup cleanup (SDD 16.6): completes file_operations, removes only
    recognized temporary paths. Never follows links and never walks outside
    data/tmp, data/trash or the document checkpoint folders."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        logs: LogService,
        data_dir: Path,
        file_journal,
    ) -> None:
        self._conn = conn
        self._logs = logs
        self._data_dir = data_dir
        self._journal = file_journal

    def run(self, *, recover: bool = True) -> dict[str, int]:
        import shutil

        counts = {"tmp": 0, "trash": 0, "recovered": 0}
        if recover:
            messages = self._journal.recover()
            counts["recovered"] = len(messages)
        tmp = tmp_dir(self._data_dir)
        if tmp.exists():
            for entry in tmp.iterdir():
                if entry.name.startswith(("import-", "edit-")):
                    shutil.rmtree(entry, ignore_errors=True)
                    counts["tmp"] += 1
        trash = trash_dir(self._data_dir)
        if trash.exists():
            for entry in trash.iterdir():
                shutil.rmtree(entry, ignore_errors=True)
                counts["trash"] += 1
        self._logs.record(
            "INFO",
            "system.cleanup",
            "startup cleanup finished",
            LogContext(correlation_id=new_correlation_id()),
            fields=(("tmp", counts["tmp"]), ("trash", counts["trash"])),
        )
        return counts

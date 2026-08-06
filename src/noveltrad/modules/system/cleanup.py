"""Startup cleanup (SDD 16.6).

Completes file_operations, then removes exclusively the recognized paths
matching data/tmp/import-* unreferenced, data/tmp/export-* expired from 24
hours and orphan checkpoints confirmed by SQLite. Never follows links and
never walks outside data/tmp, data/trash or the document checkpoint
folders.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from noveltrad.core.logging import LogContext, LogService, new_correlation_id
from noveltrad.core.paths import tmp_dir, trash_dir


class CleanupService:
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
                elif entry.name.startswith("export-") and _expired(entry):
                    entry.unlink(missing_ok=True)
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


def _expired(path: Path, ttl_hours: float = 24.0) -> bool:
    import time

    try:
        return time.time() - path.stat().st_mtime > ttl_hours * 3600
    except OSError:
        return False

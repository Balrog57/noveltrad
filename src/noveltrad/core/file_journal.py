"""file_operations journal state machine (SDD 8.8.4, 8.13).

Keeps SQLite and the filesystem consistent. Any mutation touching both
resources goes through this journal and is recoverable or compensable at
each cut point; it never claims to be a single transaction across the two
resources.

Phases: PREPARED -> DB_COMMITTED -> PUBLISHED (entry removed after success).
At startup a DB_COMMITTED phase finishes the rename after hash check; a
missing or corrupt staged batch compensates by removing the created
business row and logs the failure.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import TypeVar

from .atomic_files import rename_atomic
from .clock import utc_now
from .exceptions import StorageError
from .paths import resolve

T = TypeVar("T")

_OPERATIONS = (
    "IMPORT_DOCUMENT",
    "RESET_DOCUMENT",
    "EDIT_DOCUMENT",
    "EDIT_PROJECT",
    "DELETE_DOCUMENT",
    "DELETE_PROJECT",
)
_PHASES = ("PREPARED", "DB_COMMITTED", "PUBLISHED")


class FileJournal:
    """Persisted journal reconciling SQLite with the filesystem."""

    def __init__(self, conn: sqlite3.Connection, data_dir) -> None:
        self._conn = conn
        self._data_dir = data_dir

    # -- writes -----------------------------------------------------------

    def insert_prepared(
        self,
        operation: str,
        target_path: str,
        *,
        staged_path: str | None = None,
        project_id: int | None = None,
        document_id: int | None = None,
        payload_hash: str | None = None,
    ) -> int:
        if operation not in _OPERATIONS or staged_path and staged_path.startswith("/"):
            raise StorageError("invalid file operation")
        now = utc_now().isoformat()
        cur = self._conn.execute(
            "INSERT INTO file_operations "
            "(operation, project_id, document_id, staged_path, target_path, "
            "payload_hash, phase, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'PREPARED', ?, ?)",
            (operation, project_id, document_id, staged_path, target_path, payload_hash, now, now),
        )
        return int(cur.lastrowid)

    def advance_to_db_committed(self, operation_id: int) -> None:
        self._conn.execute(
            "UPDATE file_operations SET phase='DB_COMMITTED', updated_at=? "
            "WHERE id=? AND phase='PREPARED'",
            (utc_now().isoformat(), operation_id),
        )

    def advance_to_published(self, operation_id: int) -> None:
        now = utc_now().isoformat()
        self._conn.execute(
            "UPDATE file_operations SET phase='PUBLISHED', updated_at=? "
            "WHERE id=? AND phase='DB_COMMITTED'",
            (now, operation_id),
        )

    def remove(self, operation_id: int) -> None:
        self._conn.execute("DELETE FROM file_operations WHERE id=?", (operation_id,))

    def pending(self, phase: str | None = None) -> list[sqlite3.Row]:
        if phase:
            rows = self._conn.execute(
                "SELECT * FROM file_operations WHERE phase=? ORDER BY id", (phase,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM file_operations ORDER BY id").fetchall()
        return rows

    # -- recovery ---------------------------------------------------------

    def recover(
        self,
        remove_business_row: Callable[[str, int | None, int | None], None] | None = None,
        restore_target: Callable[[str, str], None] | None = None,
        verify_hash: Callable[[str, str | None], bool] | None = None,
    ) -> list[str]:
        """Recover or compensate interrupted operations at startup (8.13).

        For each DB_COMMITTED operation: verify the staged batch hash, then
        finish the rename to target and publish. A missing/corrupt batch is
        compensated by removing the created business row. For PREPARED
        delete operations the target is restored. Returns a list of
        diagnostic messages (already safe).
        """
        messages: list[str] = []
        for row in self.pending("DB_COMMITTED"):
            operation_id = int(row["id"])
            staged = row["staged_path"]
            target = row["target_path"]
            expected = row["payload_hash"]
            ok = True
            if staged is not None:
                staged_path = resolve(self._data_dir, staged)
                ok = staged_path.exists() and (
                    verify_hash is None or verify_hash(str(staged_path), expected)
                )
            if ok:
                if staged is not None and staged != target:
                    try:
                        rename_atomic(staged_path, resolve(self._data_dir, target))
                    except StorageError as exc:
                        messages.append(f"operation {operation_id}: {exc}")
                        continue
                self.advance_to_published(operation_id)
                self.remove(operation_id)
            else:
                if remove_business_row is not None:
                    remove_business_row(
                        row["operation"],
                        row["project_id"],
                        row["document_id"],
                    )
                self.remove(operation_id)
                messages.append(
                    f"operation {operation_id} compensated: staged batch missing or corrupt"
                )
        for row in self.pending("PREPARED"):
            operation_id = int(row["id"])
            target = row["target_path"]
            staged = row["staged_path"]
            if row["operation"].startswith("DELETE") and staged and restore_target is not None:
                staged_path = resolve(self._data_dir, staged)
                if staged_path.exists():
                    try:
                        restore_target(staged, target)
                    except StorageError as exc:
                        messages.append(f"operation {operation_id}: {exc}")
                        continue
            self.remove(operation_id)
        return messages

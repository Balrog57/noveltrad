"""Project persistence (SDD 8.5). Only read/write operations, no business."""

from __future__ import annotations

import sqlite3

from noveltrad.core.clock import utc_now
from noveltrad.core.contracts import LanguageCode, ProjectId, ProjectStatus
from noveltrad.core.exceptions import IntegrityError

from .models import ProjectRow

_COLUMNS = (
    "id, name, source_language, target_language, status, created_at, updated_at, "
    "completion_notice_claimed_at, completion_notice_acknowledged_at"
)


def _row_to_project(row: sqlite3.Row) -> ProjectRow:
    return ProjectRow(
        id=row["id"],
        name=row["name"],
        source_language=row["source_language"],
        target_language=row["target_language"],
        status=ProjectStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completion_notice_claimed_at=row["completion_notice_claimed_at"],
        completion_notice_acknowledged_at=row["completion_notice_acknowledged_at"],
    )


class ProjectRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, name: str, target_language: LanguageCode) -> ProjectRow:
        now = utc_now().isoformat()
        cur = self._conn.execute(
            "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
            "VALUES (?, ?, 'Draft', ?, ?)",
            (name, target_language, now, now),
        )
        return self.get_by_id(ProjectId(int(cur.lastrowid)))

    def get_by_id(self, project_id: ProjectId) -> ProjectRow:
        row = self._conn.execute(
            f"SELECT {_COLUMNS} FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        if row is None:
            raise IntegrityError(f"project {project_id} not found")
        return _row_to_project(row)

    def list_all(self, query: str | None = None) -> list[ProjectRow]:
        if query:
            like = f"%{query}%"
            rows = self._conn.execute(
                f"SELECT {_COLUMNS} FROM projects WHERE name LIKE ? "
                "ORDER BY updated_at DESC, id DESC",
                (like,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                f"SELECT {_COLUMNS} FROM projects ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [_row_to_project(r) for r in rows]

    def update_name(self, project_id: ProjectId, name: str) -> ProjectRow:
        self._conn.execute(
            "UPDATE projects SET name=?, updated_at=? WHERE id=?",
            (name, utc_now().isoformat(), project_id),
        )
        return self.get_by_id(project_id)

    def update_status(self, project_id: ProjectId, status: str) -> None:
        self._conn.execute(
            "UPDATE projects SET status=?, updated_at=? WHERE id=?",
            (status, utc_now().isoformat(), project_id),
        )

    def update_source_language(self, project_id: ProjectId, source_language: str | None) -> None:
        self._conn.execute(
            "UPDATE projects SET source_language=?, updated_at=? WHERE id=?",
            (source_language, utc_now().isoformat(), project_id),
        )

    def delete(self, project_id: ProjectId) -> None:
        self._conn.execute("DELETE FROM projects WHERE id=?", (project_id,))

    def claim_completion_notice(self, project_id: ProjectId) -> bool:
        """Atomically claim the terminal notice; True on first claim (13.5)."""
        now = utc_now().isoformat()
        cur = self._conn.execute(
            "UPDATE projects SET completion_notice_claimed_at=?, updated_at=? "
            "WHERE id=? AND status='Completed' AND completion_notice_claimed_at IS NULL",
            (now, now, project_id),
        )
        return cur.rowcount == 1

    def acknowledge_completion_notice(self, project_id: ProjectId) -> None:
        self._conn.execute(
            "UPDATE projects SET completion_notice_acknowledged_at=?, updated_at=? "
            "WHERE id=? AND status='Completed'",
            (utc_now().isoformat(), utc_now().isoformat(), project_id),
        )

    def unacknowledged_completed(self) -> list[ProjectRow]:
        rows = self._conn.execute(
            f"SELECT {_COLUMNS} FROM projects WHERE status='Completed' "
            "AND completion_notice_acknowledged_at IS NULL ORDER BY id DESC"
        ).fetchall()
        return [_row_to_project(r) for r in rows]

    def count_documents(self, project_id: ProjectId) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM documents WHERE project_id=?", (project_id,)
        ).fetchone()
        return int(row["c"])

    def completed_documents(self, project_id: ProjectId) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM documents WHERE project_id=? AND status='Completed'",
            (project_id,),
        ).fetchone()
        return int(row["c"])

    def failed_documents(self, project_id: ProjectId) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM documents WHERE project_id=? AND status='Failed'",
            (project_id,),
        ).fetchone()
        return int(row["c"])

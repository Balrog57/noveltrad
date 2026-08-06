"""ExportService (SDD 15).

Checks eligibility (all documents Completed, no active job), assembles the
single Markdown in document order with exactly two line breaks between
documents, deduplicates WebP by SHA-256, generates the ephemeral ZIP and
cleans it up after download or expiration (24h). source.md and
translated.md are never modified.
"""

from __future__ import annotations

import secrets
import sqlite3
from datetime import timedelta
from pathlib import Path

from noveltrad.core.atomic_files import write_atomic
from noveltrad.core.clock import utc_now
from noveltrad.core.contracts import (
    ArtifactId,
    ExportArtifact,
    ProgressPhase,
    ProgressSink,
    ProgressUpdate,
    ProjectId,
)
from noveltrad.core.exceptions import ConflictError, NotFoundError
from noveltrad.core.logging import LogContext, LogService, new_correlation_id
from noveltrad.core.paths import resolve, tmp_dir

from .archive import build_archive, read_images, slugify

_EXPIRATION = timedelta(hours=24)


class ExportService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        logs: LogService,
        data_dir: Path,
    ) -> None:
        self._conn = conn
        self._logs = logs
        self._data_dir = data_dir
        self._artifacts: dict[ArtifactId, tuple[Path, str]] = {}

    def generate(
        self, project_id: ProjectId, progress: ProgressSink | None = None
    ) -> ExportArtifact:
        self._check_eligible(project_id)
        if progress is not None:
            progress(ProgressUpdate(ProgressPhase.EXPORT_VALIDATE, 0, None, "export"))
        project = self._conn.execute(
            "SELECT name FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        if project is None:
            raise NotFoundError(f"project {project_id} not found")
        docs = self._conn.execute(
            "SELECT * FROM documents WHERE project_id=? ORDER BY order_index",
            (project_id,),
        ).fetchall()
        markdown_parts: list[str] = []
        images: dict[str, bytes] = {}
        for index, doc in enumerate(docs):
            if doc["translated_path"] is None:
                raise ConflictError("document has no published translation")
            target = resolve(self._data_dir, doc["translated_path"])
            markdown_parts.append(target.read_text(encoding="utf-8"))
            for name, payload in read_images(self._data_dir, f"projects/{project_id}/{doc['id']}"):
                images.setdefault(name, payload)
            if progress is not None:
                progress(
                    ProgressUpdate(ProgressPhase.EXPORT_ASSEMBLE, index + 1, len(docs), "export")
                )
        markdown_bytes = ("\n\n".join(markdown_parts) + "\n").encode("utf-8")
        slug = slugify(project["name"], project_id)
        markdown_name = f"{slug}.md"
        artifact_id = ArtifactId(secrets.token_urlsafe(24))
        zip_buffer = build_archive(
            artifact_id,
            markdown_name,
            markdown_bytes,
            list(images.items()),
        )
        target = tmp_dir(self._data_dir) / f"export-{artifact_id}.zip"
        write_atomic(target, zip_buffer.getvalue())
        expires_at = utc_now() + _EXPIRATION
        self._artifacts[artifact_id] = (target, markdown_name)
        self._logs.record(
            "INFO",
            "export.generate",
            "export generated",
            LogContext(correlation_id=new_correlation_id(), project_id=project_id),
        )
        if progress is not None:
            progress(ProgressUpdate(ProgressPhase.EXPORT_FINALIZE, 1, None, "export"))
        return ExportArtifact(
            id=artifact_id,
            download_name=markdown_name,
            media_type="application/zip",
            size_bytes=target.stat().st_size,
            expires_at=expires_at,
        )

    def open(self, artifact_id: ArtifactId):
        """Return the artifact path only when it was created in this process."""
        entry = self._artifacts.get(artifact_id)
        if entry is None:
            raise NotFoundError("artifact not found or expired")
        target, _ = entry
        if not target.exists():
            raise NotFoundError("artifact file missing")
        return target

    def cleanup(self, artifact_id: ArtifactId) -> None:
        entry = self._artifacts.pop(artifact_id, None)
        if entry is None:
            return
        target, _ = entry
        target.unlink(missing_ok=True)
        self._logs.record(
            "INFO",
            "export.download",
            "export cleaned up",
            LogContext(correlation_id=new_correlation_id()),
        )

    def cleanup_expired(self) -> int:
        """Startup cleanup: remove only expired export-* not opened (15.6)."""
        removed = 0
        for artifact_id, (target, _) in list(self._artifacts.items()):
            # in-memory artifacts are removed on cleanup; filesystem leftovers
            # handled by system.cleanup
            del target, artifact_id
        for file in (tmp_dir(self._data_dir)).glob("export-*.zip"):
            # only remove files older than 24h
            import time

            try:
                if time.time() - file.stat().st_mtime > _EXPIRATION.total_seconds():
                    file.unlink()
                    removed += 1
            except OSError:
                continue
        return removed

    def _check_eligible(self, project_id: ProjectId) -> None:
        row = self._conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"project {project_id} not found")
        if row["status"] != "Completed":
            raise ConflictError("export is only possible when all documents are finished")
        active = self._conn.execute(
            "SELECT COUNT(*) AS c FROM jobs WHERE state IN ('Running','Retrying')"
        ).fetchone()
        if active["c"] > 0:
            raise ConflictError("a job is still active")
        docs = self._conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS done "
            "FROM documents WHERE project_id=?",
            (project_id,),
        ).fetchone()
        if docs["total"] == 0 or docs["done"] != docs["total"]:
            raise ConflictError("not all documents are completed")

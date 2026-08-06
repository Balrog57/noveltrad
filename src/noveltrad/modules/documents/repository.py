"""Document persistence (SDD 8.6). Only read/write operations."""

from __future__ import annotations

import sqlite3

from noveltrad.core.clock import utc_now
from noveltrad.core.contracts import (
    ChapterId,
    DocumentId,
    ProjectId,
    SegmentId,
)
from noveltrad.core.exceptions import NotFoundError

from .models import ChapterRow, DocumentRow, SegmentRow

_DOC_COLUMNS = (
    "id, project_id, display_name, import_format, order_index, source_path, "
    "source_hash, translated_path, translated_hash, status, progress, word_count, "
    "character_count, detected_language, last_error, updated_at"
)
_CHAP_COLUMNS = (
    "id, document_id, order_index, title, source_start, source_end, source_hash, "
    "translated_start, translated_end, translated_hash"
)
_SEG_COLUMNS = (
    "id, chapter_id, order_index, source_start, source_end, source_hash, state, "
    "checkpoint_path, checkpoint_hash, retry_count, last_error, updated_at"
)


def _doc(row: sqlite3.Row) -> DocumentRow:
    from noveltrad.core.contracts import DocumentStatus

    return DocumentRow(
        id=row["id"],
        project_id=row["project_id"],
        display_name=row["display_name"],
        import_format=row["import_format"],
        order_index=row["order_index"],
        source_path=row["source_path"],
        source_hash=row["source_hash"],
        translated_path=row["translated_path"],
        translated_hash=row["translated_hash"],
        status=DocumentStatus(row["status"]),
        progress=row["progress"],
        word_count=row["word_count"],
        character_count=row["character_count"],
        detected_language=row["detected_language"],
        last_error=row["last_error"],
        updated_at=row["updated_at"],
    )


def _chap(row: sqlite3.Row) -> ChapterRow:
    return ChapterRow(
        id=row["id"],
        document_id=row["document_id"],
        order_index=row["order_index"],
        title=row["title"],
        source_start=row["source_start"],
        source_end=row["source_end"],
        source_hash=row["source_hash"],
        translated_start=row["translated_start"],
        translated_end=row["translated_end"],
        translated_hash=row["translated_hash"],
    )


def _seg(row: sqlite3.Row) -> SegmentRow:
    return SegmentRow(
        id=row["id"],
        chapter_id=row["chapter_id"],
        order_index=row["order_index"],
        source_start=row["source_start"],
        source_end=row["source_end"],
        source_hash=row["source_hash"],
        state=row["state"],
        checkpoint_path=row["checkpoint_path"],
        checkpoint_hash=row["checkpoint_hash"],
        retry_count=row["retry_count"],
        last_error=row["last_error"],
        updated_at=row["updated_at"],
    )


class DocumentRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # -- documents --------------------------------------------------------

    def insert_document(
        self,
        project_id: ProjectId,
        display_name: str,
        import_format: str,
        order_index: int,
        source_path: str,
        source_hash: str,
        detected_language: str | None,
        word_count: int,
        character_count: int,
    ) -> DocumentRow:
        now = utc_now().isoformat()
        cur = self._conn.execute(
            "INSERT INTO documents (project_id, display_name, import_format, order_index, "
            "source_path, source_hash, translated_path, translated_hash, status, progress, "
            "word_count, character_count, detected_language, last_error, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 'ToTranslate', 0.0, ?, ?, ?, NULL, ?)",
            (
                project_id,
                display_name,
                import_format,
                order_index,
                source_path,
                source_hash,
                word_count,
                character_count,
                detected_language,
                now,
            ),
        )
        return self.get_document(DocumentId(int(cur.lastrowid)))

    def get_document(self, document_id: DocumentId) -> DocumentRow:
        row = self._conn.execute(
            f"SELECT {_DOC_COLUMNS} FROM documents WHERE id=?", (document_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"document {document_id} not found")
        return _doc(row)

    def list_documents(self, project_id: ProjectId) -> list[DocumentRow]:
        rows = self._conn.execute(
            f"SELECT {_DOC_COLUMNS} FROM documents WHERE project_id=? ORDER BY order_index",
            (project_id,),
        ).fetchall()
        return [_doc(r) for r in rows]

    def next_order_index(self, project_id: ProjectId) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(order_index), -1) + 1 AS n FROM documents WHERE project_id=?",
            (project_id,),
        ).fetchone()
        return int(row["n"])

    def update_status(self, document_id: DocumentId, status: str, progress: float) -> None:
        self._conn.execute(
            "UPDATE documents SET status=?, progress=?, updated_at=? WHERE id=?",
            (status, progress, utc_now().isoformat(), document_id),
        )

    def update_progress(self, document_id: DocumentId, progress: float) -> None:
        self._conn.execute(
            "UPDATE documents SET progress=?, updated_at=? WHERE id=?",
            (progress, utc_now().isoformat(), document_id),
        )

    def update_detected_language(self, document_id: DocumentId, language: str) -> None:
        self._conn.execute(
            "UPDATE documents SET detected_language=?, updated_at=? WHERE id=?",
            (language, utc_now().isoformat(), document_id),
        )

    def set_translated(
        self, document_id: DocumentId, translated_path: str, translated_hash: str
    ) -> None:
        self._conn.execute(
            "UPDATE documents SET translated_path=?, translated_hash=?, updated_at=? WHERE id=?",
            (translated_path, translated_hash, utc_now().isoformat(), document_id),
        )

    def update_translated_hash(self, document_id: DocumentId, translated_hash: str) -> None:
        self._conn.execute(
            "UPDATE documents SET translated_hash=?, updated_at=? WHERE id=?",
            (translated_hash, utc_now().isoformat(), document_id),
        )

    def reorder(self, project_id: ProjectId, document_ids: list[DocumentId]) -> None:
        """Reassign order_index safely (temporary offset avoids UNIQUE clash)."""
        offset = len(document_ids)
        for document_id in document_ids:
            self._conn.execute(
                "UPDATE documents SET order_index=?, updated_at=? WHERE id=? AND project_id=?",
                (offset, utc_now().isoformat(), document_id, project_id),
            )
            offset += 1
        for index, document_id in enumerate(document_ids):
            self._conn.execute(
                "UPDATE documents SET order_index=?, updated_at=? WHERE id=? AND project_id=?",
                (index, utc_now().isoformat(), document_id, project_id),
            )

    def delete_document(self, document_id: DocumentId) -> None:
        self._conn.execute("DELETE FROM documents WHERE id=?", (document_id,))

    def set_error(self, document_id: DocumentId, safe_message: str) -> None:
        self._conn.execute(
            "UPDATE documents SET last_error=?, status='Failed', updated_at=? WHERE id=?",
            (safe_message, utc_now().isoformat(), document_id),
        )

    # -- chapters ---------------------------------------------------------

    def insert_chapter(
        self,
        document_id: DocumentId,
        order_index: int,
        title: str | None,
        source_start: int,
        source_end: int,
        source_hash: str,
    ) -> ChapterRow:
        cur = self._conn.execute(
            "INSERT INTO chapters (document_id, order_index, title, source_start, "
            "source_end, source_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, order_index, title, source_start, source_end, source_hash),
        )
        return self.get_chapter(ChapterId(int(cur.lastrowid)))

    def get_chapter(self, chapter_id: ChapterId) -> ChapterRow:
        row = self._conn.execute(
            f"SELECT {_CHAP_COLUMNS} FROM chapters WHERE id=?", (chapter_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"chapter {chapter_id} not found")
        return _chap(row)

    def list_chapters(self, document_id: DocumentId) -> list[ChapterRow]:
        rows = self._conn.execute(
            f"SELECT {_CHAP_COLUMNS} FROM chapters WHERE document_id=? ORDER BY order_index",
            (document_id,),
        ).fetchall()
        return [_chap(r) for r in rows]

    def set_chapter_translated_range(
        self,
        chapter_id: ChapterId,
        start: int,
        end: int,
        hash_value: str,
    ) -> None:
        self._conn.execute(
            "UPDATE chapters SET translated_start=?, translated_end=?, "
            "translated_hash=? WHERE id=?",
        )

    def clear_chapter_translated_range(self, chapter_id: ChapterId) -> None:
        self._conn.execute(
            "UPDATE chapters SET translated_start=NULL, translated_end=NULL, translated_hash=NULL "
            "WHERE id=?",
            (chapter_id,),
        )

    # -- segments ---------------------------------------------------------

    def insert_segment(
        self,
        chapter_id: int,
        order_index: int,
        source_start: int,
        source_end: int,
        source_hash: str,
    ) -> SegmentRow:
        now = utc_now().isoformat()
        cur = self._conn.execute(
            "INSERT INTO segments (chapter_id, order_index, source_start, source_end, "
            "source_hash, state, updated_at) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
            (chapter_id, order_index, source_start, source_end, source_hash, now),
        )
        return self.get_segment(SegmentId(int(cur.lastrowid)))

    def get_segment(self, segment_id: SegmentId) -> SegmentRow:
        row = self._conn.execute(
            f"SELECT {_SEG_COLUMNS} FROM segments WHERE id=?", (segment_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"segment {segment_id} not found")
        return _seg(row)

    def list_segments(self, chapter_id: int) -> list[SegmentRow]:
        rows = self._conn.execute(
            f"SELECT {_SEG_COLUMNS} FROM segments WHERE chapter_id=? ORDER BY order_index",
            (chapter_id,),
        ).fetchall()
        return [_seg(r) for r in rows]

    def segments_by_document(self, document_id: DocumentId) -> list[SegmentRow]:
        rows = self._conn.execute(
            f"SELECT {_SEG_COLUMNS} FROM segments "
            "WHERE chapter_id IN (SELECT id FROM chapters WHERE document_id=?) "
            "ORDER BY chapter_id, order_index",
            (document_id,),
        ).fetchall()
        return [_seg(r) for r in rows]

    def set_segment_state(
        self,
        segment_id: SegmentId,
        state: str,
        checkpoint_path: str | None,
        checkpoint_hash: str | None,
    ) -> None:
        self._conn.execute(
            "UPDATE segments SET state=?, checkpoint_path=?, checkpoint_hash=?, "
            "retry_count=0, last_error=NULL, updated_at=? WHERE id=?",
            (state, checkpoint_path, checkpoint_hash, utc_now().isoformat(), segment_id),
        )

    def set_segment_retry(
        self,
        segment_id: SegmentId,
        retry_count: int,
        safe_error: str,
    ) -> None:
        self._conn.execute(
            "UPDATE segments SET retry_count=?, last_error=?, updated_at=? WHERE id=?",
            (retry_count, safe_error, utc_now().isoformat(), segment_id),
        )

    def reset_document_segments(self, document_id: DocumentId) -> None:
        self._conn.execute(
            "UPDATE segments SET state='PENDING', checkpoint_path=NULL, "
            "checkpoint_hash=NULL, retry_count=0, last_error=NULL, updated_at=? "
            "WHERE chapter_id IN (SELECT id FROM chapters WHERE document_id=?)",
            (utc_now().isoformat(), document_id),
        )
        for chapter in self.list_chapters(document_id):
            self.clear_chapter_translated_range(chapter.id)

    def delete_checkpoints(self, document_id: DocumentId) -> None:
        self._conn.execute(
            "UPDATE segments SET checkpoint_path=NULL, checkpoint_hash=NULL, updated_at=? "
            "WHERE chapter_id IN (SELECT id FROM chapters WHERE document_id=?)",
            (utc_now().isoformat(), document_id),
        )

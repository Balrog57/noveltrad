"""DocumentService (SDD 5.8, 9.3-9.8, 10, 13.5).

Imports, converts, orders, edits, replaces, deletes and recomputes
documents. Imports run synchronously in the Streamlit process in bounded
stream with a ProgressSink; source.md is immutable.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

from noveltrad.core.atomic_files import copy_atomic, ensure_free_space, write_atomic
from noveltrad.core.clock import utc_now
from noveltrad.core.contracts import (
    Chapter,
    ChapterId,
    Document,
    DocumentId,
    EditableChapter,
    ImportBatchResult,
    ImportFailure,
    ImportSource,
    ProgressPhase,
    ProgressSink,
    ProgressUpdate,
    ProjectId,
    SearchReplacePreview,
)
from noveltrad.core.exceptions import (
    ConflictError,
    ImportConversionError,
    LockedError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from noveltrad.core.file_journal import FileJournal
from noveltrad.core.logging import LogContext, LogService, new_correlation_id
from noveltrad.core.paths import document_dir, resolve, tmp_dir
from noveltrad.core.transactions import UnitOfWork

from .adapters.docx import convert_docx
from .adapters.epub import convert_epub
from .adapters.markdown import GfmValidator, convert_markdown
from .adapters.protocol import ConvertedDocument
from .adapters.srt import convert_srt
from .adapters.text import convert_txt
from .images import convert_markdown_images, validate_references
from .language import detect_language
from .limits import MAX_BATCH_BYTES, MAX_BATCH_FILES, MIN_FREE_SPACE, SUPPORTED_EXTENSIONS
from .models import to_chapter, to_document
from .repository import DocumentRepository

_ADAPTERS = {
    "epub": convert_epub,
    "docx": convert_docx,
    "md": convert_markdown,
    "txt": convert_txt,
    "srt": convert_srt,
}

_REPLACE_TOKEN_TTL = timedelta(minutes=10)


class DocumentService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        repository: DocumentRepository,
        logs: LogService,
        data_dir: Path,
    ) -> None:
        self._conn = conn
        self._repo = repository
        self._logs = logs
        self._data_dir = data_dir
        self._journal = FileJournal(conn, data_dir)
        self._locks: dict[int, threading.Lock] = {}
        self._replace_previews: dict[str, tuple[int, str, str, dict[int, str], datetime]] = {}

    def _lock_for(self, document_id: DocumentId) -> threading.Lock:
        return self._locks.setdefault(document_id, threading.Lock())

    # -- import -----------------------------------------------------------

    def import_batch(
        self,
        project_id: ProjectId,
        sources: Sequence[ImportSource],
        progress: ProgressSink | None = None,
    ) -> ImportBatchResult:
        self._ensure_project(project_id)
        self._ensure_unlocked(project_id)
        if len(sources) > MAX_BATCH_FILES:
            raise ValidationError(f"at most {MAX_BATCH_FILES} files per batch")
        total_bytes = sum(s.size_bytes for s in sources)
        if total_bytes > MAX_BATCH_BYTES:
            raise ValidationError("batch exceeds 512 Mio")
        ensure_free_space(self._data_dir, max(MIN_FREE_SPACE, 2 * total_bytes))

        imported: list[Document] = []
        failures: list[ImportFailure] = []
        for index, source in enumerate(sources):
            if progress is not None:
                progress(ProgressUpdate(ProgressPhase.IMPORT_COPY, index, len(sources), "import"))
            try:
                document = self._import_one(project_id, source)
                imported.append(document)
            except ImportConversionError as exc:
                failures.append(ImportFailure(source.filename, exc.error_code, exc.safe_message))
            except StorageError as exc:
                failures.append(ImportFailure(source.filename, "IMPORT_FAILED", str(exc)))
        if progress is not None:
            progress(ProgressUpdate(ProgressPhase.IMPORT_PUBLISH, len(imported), None, "done"))
        return ImportBatchResult(documents=tuple(imported), failures=tuple(failures))

    def _import_one(self, project_id: ProjectId, source: ImportSource) -> Document:
        extension = Path(source.filename).suffix.lower().lstrip(".")
        if extension not in SUPPORTED_EXTENSIONS:
            raise ImportConversionError("FORMAT_UNSUPPORTED", "format not supported")
        if source.size_bytes > 512 * 1024 * 1024:
            raise ImportConversionError("FILE_TOO_LARGE", "file exceeds 512 Mio")

        operation_id = uuid.uuid4().hex
        batch_dir = tmp_dir(self._data_dir) / f"import-{operation_id}"
        batch_dir.mkdir(parents=True, exist_ok=True)
        temp_copy = batch_dir / source.filename
        try:
            with source.stream:
                _copy_stream_to_file(source.stream, temp_copy)
            converted = _ADAPTERS[extension](temp_copy, batch_dir)
            if isinstance(converted, ImportFailure):
                raise ImportConversionError(converted.error_code, converted.safe_message)
            return self._publish_conversion(
                project_id, source.filename, converted, batch_dir, operation_id
            )
        except OSError as exc:
            raise StorageError(f"import copy failed: {exc}") from exc
        finally:
            import shutil

            shutil.rmtree(batch_dir, ignore_errors=True)

    def _publish_conversion(
        self,
        project_id: ProjectId,
        filename: str,
        converted: ConvertedDocument,
        batch_dir: Path,
        operation_id: str,
    ) -> Document:
        # 1. Post-process: embed images, validate GFM, detect language.
        markdown = convert_markdown_images(converted.source_markdown, batch_dir)
        validator = GfmValidator()
        if not validator.is_valid(markdown):
            raise ImportConversionError("MD_INVALID", "converted Markdown is invalid")
        image_errors = validate_references(markdown, batch_dir)
        if image_errors:
            raise ImportConversionError("IMAGE_MISSING", image_errors[0])
        language = converted.detected_language or detect_language(markdown)
        source_bytes = markdown.encode("utf-8")
        source_hash = hashlib.sha256(source_bytes).hexdigest()

        # 2. Stage the immutable source.md under data/tmp/import-<op>.
        staged_source = batch_dir / "source.md"
        write_atomic(staged_source, source_bytes)

        target_rel = f"projects/{project_id}/<docid>/source.md"

        # 3. Transaction: insert document + journal row (DB_COMMITTED).
        order_index = self._repo.next_order_index(project_id)
        with UnitOfWork(self._conn, immediate=True):
            doc = self._repo.insert_document(
                project_id,
                Path(filename).stem,
                Path(filename).suffix.lower().lstrip("."),
                order_index,
                target_rel,
                source_hash,
                None if language == "und" else language,
                converted.word_count,
                converted.character_count,
            )
            target_rel = f"projects/{project_id}/{doc.id}/source.md"
            self._conn.execute(
                "UPDATE documents SET source_path=? WHERE id=?",
                (target_rel, doc.id),
            )
            op_id = self._journal.insert_prepared(
                "IMPORT_DOCUMENT",
                target_rel,
                staged_path=f"tmp/import-{operation_id}/source.md",
                project_id=project_id,
                document_id=doc.id,
                payload_hash=source_hash,
            )
            self._journal.advance_to_db_committed(op_id)

        # 4. Publish: rename staged batch into the document directory.
        final_dir = document_dir(self._data_dir, project_id, doc.id)
        final_dir.mkdir(parents=True, exist_ok=True)
        if (batch_dir / "images").exists():
            copy_atomic(batch_dir / "images", final_dir / "images")
        from noveltrad.core.atomic_files import rename_atomic

        rename_atomic(staged_source, final_dir / "source.md")
        if (batch_dir / "images").exists():
            import shutil

            shutil.rmtree(final_dir / "images", ignore_errors=True)
            shutil.move(str(batch_dir / "images"), str(final_dir / "images"))
        self._journal.advance_to_published(op_id)
        self._journal.remove(op_id)

        for chapter_index, (index, title) in enumerate(converted.chapters):
            offset = _chapter_offset(markdown, title) if converted.chapters == ((0, None),) else 0
            self._repo.insert_chapter(doc.id, index, title, 0, len(source_bytes), source_hash)
            del chapter_index, offset

        self._logs.record(
            "INFO",
            "document.import",
            "document imported",
            LogContext(
                correlation_id=new_correlation_id(),
                project_id=project_id,
                document_id=doc.id,
            ),
            fields=(("format", doc.import_format), ("words", doc.word_count)),
        )
        return to_document(self._repo.get_document(doc.id))

    # -- queries ----------------------------------------------------------

    def list(self, project_id: ProjectId) -> tuple[Document, ...]:
        self._ensure_project(project_id)
        return tuple(to_document(r) for r in self._repo.list_documents(project_id))

    def list_chapters(self, document_id: DocumentId) -> tuple[Chapter, ...]:
        return tuple(to_chapter(r) for r in self._repo.list_chapters(document_id))

    def load_editable_chapter(self, chapter_id: ChapterId) -> EditableChapter:
        chapter = self._repo.get_chapter(chapter_id)
        document = self._repo.get_document(chapter.document_id)
        if document.translated_path is None:
            raise LockedError("translation not published yet")
        target = resolve(self._data_dir, document.translated_path)
        content = _read_range(target, chapter.translated_start, chapter.translated_end)
        return EditableChapter(
            chapter_id=chapter.id,
            markdown=content,
            content_hash=chapter.translated_hash or "",
            updated_at=utc_now(),
        )

    # -- ordering ---------------------------------------------------------

    def reorder(
        self, project_id: ProjectId, document_ids: Sequence[DocumentId]
    ) -> tuple[Document, ...]:
        self._ensure_project(project_id)
        self._ensure_unlocked(project_id)
        existing = {doc.id for doc in self._repo.list_documents(project_id)}
        if set(document_ids) != existing or len(document_ids) != len(existing):
            raise ValidationError("document set mismatch")
        with UnitOfWork(self._conn):
            self._repo.reorder(project_id, list(document_ids))
        return tuple(to_document(r) for r in self._repo.list_documents(project_id))

    # -- deletion ---------------------------------------------------------

    def delete(self, document_id: DocumentId, confirmation: str | None) -> None:
        doc = self._repo.get_document(document_id)
        self._ensure_unlocked(doc.project_id)
        if doc.status.value == "Completed" and confirmation != f"DELETE_DOCUMENT {document_id}":
            raise ValidationError("confirmation mismatch: expected DELETE_DOCUMENT <document_id>")
        with self._lock_for(document_id):
            with UnitOfWork(self._conn):
                self._repo.delete_document(document_id)
            folder = document_dir(self._data_dir, doc.project_id, document_id)
            import shutil

            shutil.rmtree(folder, ignore_errors=True)

    # -- editing (13.5, 8.13 EDIT_DOCUMENT) --------------------------------

    def save_editable_chapter(
        self, chapter_id: ChapterId, markdown: str, expected_hash: str
    ) -> EditableChapter:
        chapter = self._repo.get_chapter(chapter_id)
        document = self._repo.get_document(chapter.document_id)
        if document.status.value != "Completed":
            raise LockedError("editing is only possible after final validation")
        if chapter.translated_hash != expected_hash:
            raise ConflictError("chapter was modified elsewhere")
        validator = GfmValidator()
        if not validator.is_valid(markdown):
            raise ValidationError("edited Markdown is invalid")
        target = resolve(self._data_dir, document.translated_path)
        content = target.read_bytes()
        start, end = chapter.translated_start, chapter.translated_end
        if start is None or end is None:
            raise ConflictError("chapter has no published range")
        new_content = content[:start] + markdown.encode("utf-8") + content[end:]
        new_hash = hashlib.sha256(new_content).hexdigest()
        markdown_bytes = markdown.encode("utf-8")
        delta = len(markdown_bytes) - (end - start)
        with self._lock_for(document.id):
            tmp_name = target.with_name(f"{target.name}.edit-{uuid.uuid4().hex[:8]}")
            write_atomic(tmp_name, new_content)
            os.replace(tmp_name, target)
            with UnitOfWork(self._conn):
                self._repo.set_chapter_translated_range(
                    chapter_id,
                    start,
                    start + len(markdown_bytes),
                    hashlib.sha256(markdown_bytes).hexdigest(),
                )
                self._shift_following_ranges(document.id, chapter.order_index, delta)
                self._repo.update_translated_hash(document.id, new_hash)
        return EditableChapter(
            chapter_id=chapter_id,
            markdown=markdown,
            content_hash=hashlib.sha256(markdown_bytes).hexdigest(),
            updated_at=utc_now(),
        )

    def _shift_following_ranges(
        self, document_id: DocumentId, chapter_index: int, delta: int
    ) -> None:
        for chapter in self._repo.list_chapters(document_id):
            if chapter.order_index > chapter_index and chapter.translated_start is not None:
                self._conn.execute(
                    "UPDATE chapters SET translated_start=translated_start+?, "
                    "translated_end=translated_end+? WHERE id=?",
                    (delta, delta, chapter.id),
                )

    # -- global replace (EF-012, 13.5) --------------------------------------

    def preview_replace(
        self, project_id: ProjectId, needle: str, replacement: str
    ) -> SearchReplacePreview:
        self._ensure_project(project_id)
        if not needle or len(needle) > 10_000:
            raise ValidationError("needle must be 1..10000 characters")
        if len(replacement) > 10_000:
            raise ValidationError("replacement must not exceed 10000 characters")
        needle = needle.encode("utf-8").decode("utf-8")
        documents = self._repo.list_documents(project_id)
        occurrence = 0
        doc_ids: list[DocumentId] = []
        chapter_ids: list[ChapterId] = []
        chapter_hashes: dict[int, str] = {}
        for doc in documents:
            if doc.status.value != "Completed" or doc.translated_path is None:
                continue
            target = resolve(self._data_dir, doc.translated_path)
            for chapter in self._repo.list_chapters(doc.id):
                if chapter.translated_hash is None:
                    continue
                text = _read_range(target, chapter.translated_start, chapter.translated_end)
                if needle in text:
                    occurrence += text.count(needle)
                    doc_ids.append(doc.id)
                    chapter_ids.append(chapter.id)
                    chapter_hashes[chapter.id] = chapter.translated_hash
        token = uuid.uuid4().hex
        self._replace_previews[token] = (
            project_id,
            needle,
            replacement,
            chapter_hashes,
            utc_now() + _REPLACE_TOKEN_TTL,
        )
        return SearchReplacePreview(
            token=token,
            occurrences=occurrence,
            document_ids=tuple(dict.fromkeys(doc_ids)),
            chapter_ids=tuple(chapter_ids),
            expires_at=utc_now() + _REPLACE_TOKEN_TTL,
        )

    def apply_replace(self, project_id: ProjectId, preview_token: str, confirmation: str) -> int:
        if confirmation != "APPLY_REPLACE":
            raise ValidationError("confirmation mismatch: expected APPLY_REPLACE")
        entry = self._replace_previews.pop(preview_token, None)
        if entry is None:
            raise ValidationError("preview token is expired or already consumed")
        entry_project, needle, replacement, chapter_hashes, _ = entry
        if entry_project != project_id:
            raise ValidationError("preview token belongs to another project")
        documents = self._repo.list_documents(project_id)
        applied = 0
        for doc in documents:
            if doc.status.value != "Completed" or doc.translated_path is None:
                continue
            target = resolve(self._data_dir, doc.translated_path)
            content = target.read_text(encoding="utf-8")
            changed = False
            for chapter in self._repo.list_chapters(doc.id):
                if chapter.translated_hash is None or chapter.id not in chapter_hashes:
                    continue
                if chapter_hashes[chapter.id] != chapter.translated_hash:
                    raise ConflictError("chapter changed since preview")
                start, end = chapter.translated_start, chapter.translated_end
                text = _read_range(target, start, end)
                if needle in text:
                    new_text = text.replace(needle, replacement)
                    content = content[:start] + new_text + content[end:]
                    changed = True
                    applied += 1
            if changed:
                new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                with self._lock_for(doc.id):
                    write_atomic(target, content.encode("utf-8"))
                    with UnitOfWork(self._conn):
                        self._repo.update_translated_hash(doc.id, new_hash)
                        self._recompute_chapter_ranges(doc.id, target)
        return applied

    def _recompute_chapter_ranges(self, document_id: DocumentId, target: Path) -> None:
        content = target.read_text(encoding="utf-8")
        offset = 0
        for chapter in self._repo.list_chapters(document_id):
            if chapter.translated_hash is None:
                continue
            source = self._repo.get_document(document_id)
            source_path = resolve(self._data_dir, source.source_path)
            source_text = source_path.read_text(encoding="utf-8")
            src_start, src_end = chapter.source_start, chapter.source_end
            src_chunk = source_text[src_start:src_end]
            idx = content.find(src_chunk, offset)
            if idx < 0:
                # best effort: use previous end
                idx = offset
            end = min(len(content), idx + len(src_chunk))
            chunk = content[idx:end]
            self._conn.execute(
                "UPDATE chapters SET translated_start=?, translated_end=?, "
                "translated_hash=? WHERE id=?",
                (idx, end, hashlib.sha256(chunk.encode("utf-8")).hexdigest(), chapter.id),
            )
            offset = end

    # -- helpers ----------------------------------------------------------

    def _ensure_project(self, project_id: ProjectId) -> None:
        row = self._conn.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"project {project_id} not found")

    def _ensure_unlocked(self, project_id: ProjectId) -> None:
        row = self._conn.execute("SELECT status FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"project {project_id} not found")
        if row["status"] in ("Running", "Paused"):
            raise LockedError("project is locked during an active translation")


def _chapter_offset(markdown: str, title: str | None) -> int:
    del title, markdown
    return 0


def _copy_stream_to_file(stream, target: Path) -> None:
    """Copy an arbitrary binary stream to target in bounded blocks."""
    with open(target, "wb") as out:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def _read_range(path: Path, start: int | None, end: int | None) -> str:
    data = path.read_bytes()
    return data[start:end].decode("utf-8", errors="replace")

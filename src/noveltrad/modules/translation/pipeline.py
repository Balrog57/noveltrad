"""TranslationService pipeline (SDD 11).

Four mandatory sequential passes on the same model: translate -> revise ->
context -> polish. One call per segment per pass; retries never constitute
an extra pass. Every validated segment writes an immutable checkpoint
atomically, referenced in the same SQLite transition as its new state.
After each complete pass translated.md is rebuilt and atomically replaced;
after the fourth pass the final reconstruction is published with
documents.translated_hash and the contiguous translated ranges of all
chapters, then prior checkpoints are cleaned up.
"""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from pathlib import Path

from noveltrad.core.atomic_files import write_atomic
from noveltrad.core.clock import utc_now
from noveltrad.core.contracts import (
    CompletionRequest,
    CompletionResponse,
    JobId,
    PipelineResult,
    PipelineStage,
    SegmentId,
)
from noveltrad.core.exceptions import (
    ProviderError,
    ResponseValidationError,
    StorageError,
)
from noveltrad.core.logging import LogContext, LogService, new_correlation_id
from noveltrad.core.paths import document_dir, resolve
from noveltrad.core.transactions import UnitOfWork

from .prompt_loader import PromptLoader
from .providers.base import AIProvider
from .response_parser import build_envelope, parse_segment_response, validate_finish_reason
from .retry import MAX_RETRIES, compute_wait, is_permanent_code
from .segmentation import count_tokens, segment_document

_STAGE_TRANSITIONS = {
    PipelineStage.TRANSLATE: ("PENDING", "TRANSLATED"),
    PipelineStage.REVISE: ("TRANSLATED", "REVISED"),
    PipelineStage.CONTEXT: ("REVISED", "COHERENCE_CHECKED"),
    PipelineStage.POLISH: ("COHERENCE_CHECKED", "POLISHED"),
}


class TranslationService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        provider: AIProvider,
        logs: LogService,
        data_dir: Path,
        prompt_loader: PromptLoader | None = None,
        sleep: object | None = None,
    ) -> None:
        self._conn = conn
        self._provider = provider
        self._logs = logs
        self._data_dir = data_dir
        self._prompts = prompt_loader or PromptLoader()
        self._sleep = sleep or _async_sleep

    async def execute(self, job_id: JobId) -> PipelineResult:
        """Run the four passes for the job; return the pipeline result."""
        job = self._job_row(job_id)
        document = self._document_row(job["document_id"])
        snapshot = self._snapshot(job)
        self._apply_provider_url(snapshot)
        self._ensure_segments(document, snapshot)
        segments = self._segments(job["document_id"])
        if not segments:
            raise StorageError("document has no segments")

        first_unvalidated: SegmentId | None = None
        for stage in (
            PipelineStage.TRANSLATE,
            PipelineStage.REVISE,
            PipelineStage.CONTEXT,
            PipelineStage.POLISH,
        ):
            entry_state, exit_state = _STAGE_TRANSITIONS[stage]
            # Reload per pass: the previous pass advanced segment states.
            segments = self._segments(job["document_id"])
            stage_segments = [s for s in segments if s["state"] == entry_state]
            not_finished = any(s["state"] not in (exit_state, "POLISHED") for s in segments)
            if not stage_segments and not_finished:
                break
            for segment in stage_segments:
                if first_unvalidated is None:
                    first_unvalidated = segment["id"]
                validated = await self._process_segment(
                    job_id,
                    document,
                    snapshot,
                    segment,
                    stage,
                    entry_state,
                    exit_state,
                )
                if not validated:
                    return PipelineResult(job_id, False, segment["id"])
                first_unvalidated = None
            # pass complete: rebuild translated.md
            self._rebuild_translated(document, snapshot)
        else:
            self._publish_final(document)
            self._cleanup_checkpoints(document)
            self._logs.record(
                "INFO",
                "segment.validated",
                "pipeline completed",
                _ctx(job_id),
            )
            return PipelineResult(job_id, True, None)
        return PipelineResult(job_id, False, first_unvalidated)

    async def _process_segment(
        self,
        job_id: JobId,
        document,
        snapshot,
        segment,
        stage: PipelineStage,
        entry_state: str,
        exit_state: str,
    ) -> bool:
        target = self._segment_source(segment)
        if stage == PipelineStage.CONTEXT:
            context = await self._build_context(document, segment, stage)
        else:
            context = None
        system_prompt = self._prompts.load(stage)
        request_id = uuid.uuid4().hex
        envelope = build_envelope(
            request_id,
            segment["id"],
            stage.value,
            document["detected_language"] or "und",
            self._target_language(document),
            target,
            context or {},
        )
        response: CompletionResponse | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await self._provider.complete(
                    CompletionRequest(
                        request_id=request_id,
                        segment_id=segment["id"],
                        stage=stage,
                        system_prompt=system_prompt,
                        payload_json=envelope,
                        model=snapshot.model,
                        temperature=snapshot.temperature,
                        max_output_tokens=snapshot.max_output_tokens,
                    )
                )
            except ProviderError as exc:
                if not exc.recoverable or is_permanent_code(exc.error_code):
                    self._log_failure(job_id, segment, exc.error_code)
                    return False
                if attempt < MAX_RETRIES:
                    await self._wait(job_id, attempt + 1, exc.retry_after_seconds, None)
                    continue
                self._log_failure(job_id, segment, "RETRIES_EXHAUSTED")
                return False
            if response is None:
                return False
            if response.finish_reason.value != "stop":
                # retryable invalid response (11.8)
                if attempt < MAX_RETRIES:
                    await self._wait(job_id, attempt + 1, response.retry_after_seconds, None)
                    continue
                self._log_failure(job_id, segment, "BAD_FINISH_REASON")
                return False
            break

        if response is None:
            return False
        try:
            validate_finish_reason(response.finish_reason)
            content = parse_segment_response(response.text, request_id, segment["id"])
        except ResponseValidationError as exc:
            self._log_failure(job_id, segment, exc.error_code)
            return False
        self._write_checkpoint(job_id, document, segment, content, exit_state)
        return True

    def _write_checkpoint(
        self, job_id: JobId, document, segment, content: str, exit_state: str
    ) -> None:
        doc_dir = document_dir(self._data_dir, document["project_id"], document["id"])
        checkpoints_dir = doc_dir / "checkpoints" / str(segment["id"])
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        filename = f"{exit_state}-{digest}.md"
        relative = (
            f"projects/{document['project_id']}/{document['id']}/"
            f"checkpoints/{segment['id']}/{filename}"
        )
        write_atomic(checkpoints_dir / filename, content.encode("utf-8"))
        with UnitOfWork(self._conn, immediate=True):
            self._conn.execute(
                "UPDATE segments SET state=?, checkpoint_path=?, checkpoint_hash=?, "
                "retry_count=0, last_error=NULL, updated_at=? WHERE id=?",
                (exit_state, relative, digest, utc_now().isoformat(), segment["id"]),
            )
            self._conn.execute(
                "UPDATE jobs SET current_stage=?, current_segment_id=?, progress=? WHERE id=?",
                (None, None, self._progress_of(document, segment), job_id),
            )
        self._logs.record(
            "INFO",
            "segment.validated",
            "segment validated",
            LogContext(
                correlation_id=new_correlation_id(),
                job_id=job_id,
                document_id=document["id"],
            ),
            fields=(("segment_id", segment["id"]), ("state", exit_state)),
        )

    # -- helpers ----------------------------------------------------------

    def _job_row(self, job_id: JobId):
        row = self._conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise StorageError(f"job {job_id} not found")
        return row

    def _document_row(self, document_id: int):
        row = self._conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if row is None:
            raise StorageError(f"document {document_id} not found")
        return row

    def _snapshot(self, job):
        from noveltrad.modules.jobs.repository import deserialize_snapshot

        return deserialize_snapshot(job["snapshot_json"], job["snapshot_hash"])

    def _apply_provider_url(self, snapshot) -> None:
        """Pin the provider base URL from the frozen snapshot (14.15)."""
        setter = getattr(self._provider, "set_base_url", None)
        if setter is not None:
            setter(snapshot.base_url)

    def _ensure_segments(self, document, snapshot) -> None:
        """Segmentation (11.2): create PENDING segments per chapter when
        none exist yet (first run or RESTART_DOCUMENT reset)."""
        existing = self._conn.execute(
            "SELECT COUNT(*) AS c FROM segments WHERE chapter_id IN "
            "(SELECT id FROM chapters WHERE document_id=?)",
            (document["id"],),
        ).fetchone()
        if existing["c"] > 0:
            return
        chapters = self._conn.execute(
            "SELECT * FROM chapters WHERE document_id=? ORDER BY order_index",
            (document["id"],),
        ).fetchall()
        source_path = resolve(self._data_dir, document["source_path"])
        source_bytes = source_path.read_bytes()
        system_prompt = self._prompts.load(PipelineStage.TRANSLATE)
        prompt_tokens = count_tokens(system_prompt, "utf8-bytes-v1") + 128
        for chapter in chapters:
            chunk = source_bytes[chapter["source_start"] : chapter["source_end"]]
            text = chunk.decode("utf-8", errors="replace")
            segments = segment_document(
                text,
                window_tokens=snapshot.context_window_tokens,
                prompt_tokens=prompt_tokens,
                max_output_tokens=snapshot.max_output_tokens,
                tokenizer_mode="utf8-bytes-v1",
            )
            with UnitOfWork(self._conn, immediate=True):
                for index, segment in enumerate(segments):
                    raw = segment.text.encode("utf-8")
                    self._conn.execute(
                        "INSERT INTO segments (chapter_id, order_index, source_start, "
                        "source_end, source_hash, state, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
                        (
                            chapter["id"],
                            index,
                            segment.offset_start,
                            segment.offset_end,
                            hashlib.sha256(raw).hexdigest(),
                            utc_now().isoformat(),
                        ),
                    )

    def _segments(self, document_id: int):
        rows = self._conn.execute(
            "SELECT * FROM segments WHERE chapter_id IN "
            "(SELECT id FROM chapters WHERE document_id=?) ORDER BY chapter_id, order_index",
            (document_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _segment_source(self, segment) -> str:
        if segment["checkpoint_path"] is not None and segment["state"] != "PENDING":
            checkpoint = resolve(self._data_dir, segment["checkpoint_path"])
            return checkpoint.read_text(encoding="utf-8")
        chapter = self._conn.execute(
            "SELECT * FROM chapters WHERE id=?", (segment["chapter_id"],)
        ).fetchone()
        document = self._document_row(chapter["document_id"])
        source = resolve(self._data_dir, document["source_path"])
        data = source.read_bytes()
        chunk = data[segment["source_start"] : segment["source_end"]]
        return chunk.decode("utf-8", errors="replace")

    async def _build_context(self, document, segment, stage) -> dict[str, str | None]:
        """RM-008: previous translated chapter, current translated chapter,
        next source chapter — deterministic excerpts within budget."""
        chapter = self._conn.execute(
            "SELECT * FROM chapters WHERE id=?", (segment["chapter_id"],)
        ).fetchone()
        chapters = self._conn.execute(
            "SELECT * FROM chapters WHERE document_id=? ORDER BY order_index",
            (document["id"],),
        ).fetchall()
        index = next(i for i, c in enumerate(chapters) if c["id"] == chapter["id"])
        previous = chapters[index - 1] if index > 0 else None
        following = chapters[index + 1] if index < len(chapters) - 1 else None
        return {
            "previous": self._chapter_excerpt(previous, translated=True) if previous else None,
            "current": self._chapter_excerpt(chapter, translated=True),
            "next": self._chapter_excerpt(following, translated=False) if following else None,
        }

    def _chapter_excerpt(self, chapter, translated: bool) -> str | None:
        if translated and chapter["translated_start"] is not None:
            document = self._document_row(chapter["document_id"])
            if document["translated_path"]:
                path = resolve(self._data_dir, document["translated_path"])
                data = path.read_bytes()
                return data[chapter["translated_start"] : chapter["translated_end"]].decode(
                    "utf-8", errors="replace"
                )[:4096]
        if not translated:
            document = self._document_row(chapter["document_id"])
            source = resolve(self._data_dir, document["source_path"])
            data = source.read_bytes()
            return data[chapter["source_start"] : chapter["source_end"]].decode(
                "utf-8", errors="replace"
            )[:4096]
        return None

    def _rebuild_translated(self, document, snapshot) -> None:
        del snapshot
        segments = self._segments(document["id"])
        parts: list[str] = []
        for segment in segments:
            if segment["checkpoint_path"] is not None:
                checkpoint = resolve(self._data_dir, segment["checkpoint_path"])
                parts.append(checkpoint.read_text(encoding="utf-8"))
        content = "\n\n".join(parts) + ("\n" if parts else "")
        translated_path = f"projects/{document['project_id']}/{document['id']}/translated.md"
        target = resolve(self._data_dir, translated_path)
        write_atomic(target, content.encode("utf-8"))
        with UnitOfWork(self._conn):
            self._conn.execute(
                "UPDATE documents SET translated_path=?, updated_at=? WHERE id=?",
                (translated_path, utc_now().isoformat(), document["id"]),
            )

    def _publish_final(self, document) -> None:
        translated_path = f"projects/{document['project_id']}/{document['id']}/translated.md"
        target = resolve(self._data_dir, translated_path)
        content = target.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        with UnitOfWork(self._conn):
            self._conn.execute(
                "UPDATE documents SET translated_hash=?, status='Completed', progress=100.0, "
                "updated_at=? WHERE id=?",
                (digest, utc_now().isoformat(), document["id"]),
            )
            offset = 0
            for chapter in self._conn.execute(
                "SELECT * FROM chapters WHERE document_id=? ORDER BY order_index",
                (document["id"],),
            ):
                length = len(content) - offset
                chunk = content[offset : offset + length]
                self._conn.execute(
                    "UPDATE chapters SET translated_start=?, translated_end=?, "
                    "translated_hash=? WHERE id=?",
                    (offset, offset + len(chunk), hashlib.sha256(chunk).hexdigest(), chapter["id"]),
                )
                offset += len(chunk)

    def _cleanup_checkpoints(self, document) -> None:
        import shutil

        checkpoints_dir = (
            document_dir(self._data_dir, document["project_id"], document["id"]) / "checkpoints"
        )
        shutil.rmtree(checkpoints_dir, ignore_errors=True)

    def _progress_of(self, document, segment) -> float:
        rows = self._segments(document["id"])
        total = len(rows)
        done_states = ("TRANSLATED", "REVISED", "COHERENCE_CHECKED", "POLISHED")
        done = sum(1 for s in rows if s["state"] in done_states)
        return round(done / total * 100, 1) if total else 0.0

    def _log_failure(self, job_id: JobId, segment, error_code: str) -> None:
        self._conn.execute(
            "UPDATE segments SET last_error=?, retry_count=?, updated_at=? WHERE id=?",
            (error_code, min(MAX_RETRIES, 5), utc_now().isoformat(), segment["id"]),
        )
        self._conn.commit()
        self._logs.record(
            "ERROR",
            "job.failed",
            f"segment failed: {error_code}",
            _ctx(job_id),
            error_code=error_code,
        )

    async def _wait(
        self,
        job_id: JobId,
        attempt: int,
        retry_after: float | None,
        status_code: int | None,
    ) -> None:
        wait = compute_wait(attempt, retry_after, status_code=status_code)
        next_at = utc_now()
        from datetime import timedelta

        next_at = next_at + timedelta(seconds=wait)
        self._conn.execute(
            "UPDATE jobs SET state='Retrying', next_retry_at=? WHERE id=?",
            (next_at.isoformat(), job_id),
        )
        self._conn.commit()
        self._logs.record(
            "INFO",
            "job.retry",
            f"retry {attempt} in {wait}s",
            _ctx(job_id),
            fields=(("attempt", attempt), ("wait", wait)),
        )
        await self._sleep(wait)

    def _target_language(self, document) -> str:
        row = self._conn.execute(
            "SELECT target_language FROM projects WHERE id=?",
            (document["project_id"],),
        ).fetchone()
        return row["target_language"] if row else "und"


async def _async_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def _ctx(job_id: JobId) -> LogContext:
    return LogContext(correlation_id=new_correlation_id(), job_id=job_id)

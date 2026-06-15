"""Parser agent — Agent 1 of the v4 pipeline.

Reads a project source file, splits it into chunks, and pushes them
into the FastTranslator queue. The Parser receives a single task per
project with `action="parse"`. The payload includes the absolute source
file path.

The Parser does NOT touch the StateStore directly. The orchestrator is
the single writer. The Parser's job is:
  1. Detect format & extract a Document.
  2. Chunk each chapter's paragraphs.
  3. Emit one `progress` message (parsed N chunks).
  4. Emit one `done` message per chunk... NO — the Parser emits a single
     `done` message with the full chunk list in `payload["chunks"]`. The
     orchestrator (submit_chunks) decides what to do with it.
  5. Emit one `done` for the stage with `terminal=True` so the
     orchestrator does not forward it to FastTranslator — the
     orchestrator will inject the parsed chunks itself (which is what
     `submit_chunks` already does for the HTTP path).

Message shape on `done`:
    {
      "type": "done",
      "chunk_id": None,
      "stage": "parser",
      "payload": {
        "document": { "title": ..., "author": ..., "format": ... },
        "chapters": [
          { "id": ..., "title": ..., "chunks": [chunk_dict, ...] },
          ...
        ],
        "chunk_count": N,
      },
    }
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base_worker import BaseWorker
from ..formats import (
    chunk_blocks,
    chunk_paragraphs,
    prepare_project_source,
    read_document,
    write_project_manifest,
)

logger = logging.getLogger(__name__)


class Worker(BaseWorker):
    use_control_thread = True

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        payload = msg.get("payload") or {}
        if action != "parse":
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"parser: unknown action {action!r}",
            )
        # Multi-source: ``source_paths`` is a list (one project, N files).
        # Single-source back-compat: ``source_path`` is still honoured.
        raw_paths = payload.get("source_paths")
        if raw_paths:
            source_paths: list[str] = [str(p) for p in raw_paths if p]
        else:
            single = payload.get("source_path") or payload.get("path")
            source_paths = [str(single)] if single else []
        project_id = payload.get("project_id") or msg.get("chunk_id") or "project"
        project_dir = payload.get("project_dir") or str(
            Path(source_paths[0]).parent if source_paths else "."
        )
        output_path = payload.get("output_path")
        if not source_paths:
            return self._emit_error(
                None, "missing_source_path", "parser: payload.source_path(s) missing"
            )
        for sp in source_paths:
            if not Path(sp).exists():
                return self._emit_error(
                    None,
                    "source_not_found",
                    f"parser: file not found: {sp}",
                )

        chapters_payload: list[dict[str, Any]] = []
        all_manifests: list[dict[str, Any]] = []
        primary_doc_meta: dict[str, Any] = {}
        total = 0
        for source_str in source_paths:
            source = Path(source_str)
            try:
                manifest = prepare_project_source(
                    source,
                    project_dir=project_dir,
                    project_id=str(project_id),
                    output_path=output_path,
                )
                working_source = Path(manifest["working_source_path"])
                doc = read_document(working_source)
            except Exception as exc:
                logger.exception("Parser failed on %s", source)
                return self._emit_error(None, "parse_failed", str(exc))

            manifest["format_payload"] = dict(doc.metadata)
            if not primary_doc_meta:
                primary_doc_meta = dict(doc.metadata)
            # Track chapters in this file for incremental progress
            ch_in_file = len(doc.chapters)
            for ci, chap in enumerate(doc.chapters):
                if chap.blocks:
                    chunks = chunk_blocks(
                        chap.blocks,
                        chapter_id=chap.id,
                        chapter_title=chap.title,
                    )
                else:
                    chunks = chunk_paragraphs(
                        chap.paragraphs,
                        chapter_id=chap.id,
                        chapter_title=chap.title,
                    )
                # Stamp each chunk with the source file so the assembler
                # can write one output per source.
                for c in chunks:
                    c.setdefault("source_file", str(source))
                total += len(chunks)
                manifest["chapters"].append(
                    {
                        "id": chap.id,
                        "title": chap.title,
                        "metadata": chap.metadata,
                        "chunk_count": len(chunks),
                    }
                )
                manifest["chunks"].extend(
                    {
                        "id": c.get("id"),
                        "chapter_id": c.get("chapter_id"),
                        "chunk_index": c.get("chunk_index"),
                        "source_hash": c.get("source_hash"),
                        "metadata": c.get("metadata") or {},
                    }
                    for c in chunks
                )
                chapters_payload.append(
                    {
                        "id": chap.id,
                        "title": chap.title,
                        "chunk_count": len(chunks),
                        "chunks": chunks,
                        "source_file": str(source),
                    }
                )
                self._emit_progress(
                    None,
                    percent=100.0 * (ci + 1) / max(1, ch_in_file),
                    note=f"parsed chapter {ci + 1}/{ch_in_file} ({total} chunks)",
                )
            manifest["working_source_path"] = str(working_source)
            all_manifests.append(manifest)

        # Write a single combined manifest (use the first as the
        # canonical one, then merge the rest of the chapters in).
        combined = all_manifests[0]
        for extra in all_manifests[1:]:
            combined["chapters"].extend(extra.get("chapters", []))
            combined["chunks"].extend(extra.get("chunks", []))
        manifest_path = write_project_manifest(project_dir, combined)
        logger.info(
            "Parser: %d chunks from %d file(s) in %d chapters",
            total,
            len(source_paths),
            len(chapters_payload),
        )
        return self._emit_done_local(
            {
                "document": {
                    "title": primary_doc_meta.get("title", ""),
                    "author": primary_doc_meta.get("author", ""),
                    "format": primary_doc_meta.get("source_format", ""),
                },
                "chapters": chapters_payload,
                "chunk_count": total,
                "source_paths": [str(Path(p)) for p in source_paths],
                "source_path": (
                    str(source_paths[0]) if len(source_paths) == 1 else None
                ),
                "working_source_path": combined.get("working_source_path"),
                "target_path": combined.get("target_path"),
                "manifest_path": str(manifest_path),
            },
            terminal=True,
        )

    # ----- helpers -----

    def _emit_done_local(self, payload: dict[str, Any], terminal: bool = False) -> dict[str, Any]:
        if terminal:
            payload["terminal"] = True
        msg = {
            "msg_id": self.identity.worker_id + ":" + str(_counter()),
            "type": "done",
            "chunk_id": None,
            "stage": self.stage,
            "worker_id": self.worker_id,
            "payload": payload,
        }
        try:
            self.output_queue.put(msg, timeout=2.0)
        except Exception:
            logger.exception("Parser: failed to publish done message")
        return None


_counter_value = 0


def _counter() -> int:
    global _counter_value
    _counter_value += 1
    return _counter_value


__all__ = ["Worker"]

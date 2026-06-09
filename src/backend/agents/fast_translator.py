"""FastTranslator agent — Agent 2 of the v4 pipeline.

Translates a chunk with NLLB (fast local model). The orchestrator
already gave us the source text in the task payload, so we don't need
to touch the StateStore. We emit a `done` with the translated text in
`raw_translation`; the orchestrator persists it.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from .base_worker import BaseWorker

logger = logging.getLogger(__name__)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from ..engines.nllb_engine import NLLBEngine

        _engine = NLLBEngine()
    return _engine


class Worker(BaseWorker):
    use_control_thread = True

    def setup(self) -> None:
        # Force-load the model in setup so the first chunk doesn't pay
        # the init cost.
        self._engine = _get_engine()
        logger.info(
            "[%s] FastTranslator ready (available=%s, load_error=%s)",
            self.worker_id,
            self._engine.available,
            self._engine.load_error,
        )

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        if action not in ("translate", "hltl_reprocess"):
            return self._emit_error(
                chunk_id,
                "unknown_action",
                f"fast_translator: unknown action {action!r}",
            )
        source = payload.get("source_text") or ""
        if not source:
            return self._emit_error(
                chunk_id, "empty_source", "fast_translator: empty source text"
            )
        src_lang = payload.get("source_lang") or os.environ.get(
            "NOVELTRAD_SRC_LANG", "auto"
        )
        tgt_lang = payload.get("target_lang") or os.environ.get(
            "NOVELTRAD_TGT_LANG", "fr"
        )
        try:
            translated = self._engine.translate(source, src_lang, tgt_lang)
        except Exception as exc:
            logger.exception("FastTranslator crashed on chunk %s", chunk_id)
            return self._emit_error(chunk_id, "translate_failed", str(exc))
        self._emit_progress(chunk_id, percent=100.0, note="fast translated")
        return self._emit_done(
            chunk_id,
            {
                "raw_translation": translated,
                "engine": (
                    "nllb-200-distilled-600M"
                    if self._engine.available
                    else "nllb-fallback-identity"
                ),
                "status": "fast_translated",
            },
        )


__all__ = ["Worker"]

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
from ..llm_router.router import get_router

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
            engine_name = "nllb-200-distilled-600M"
        except Exception as exc:
            logger.warning("NLLB unavailable on chunk %s: %s", chunk_id, exc)
            translated = self._fallback_translate(source, src_lang, tgt_lang)
            if translated is None:
                return self._emit_error(
                    chunk_id,
                    "nllb_unavailable",
                    (
                        "NLLB is unavailable and no explicit draft fallback "
                        f"succeeded: {exc}"
                    ),
                )
            engine_name = "llm-draft-fallback"
        self._emit_progress(chunk_id, percent=100.0, note="fast translated")
        return self._emit_done(
            chunk_id,
            {
                "raw_translation": translated,
                "engine": engine_name,
                "status": "fast_translated",
            },
        )

    def _fallback_translate(
        self, source: str, source_lang: str, target_lang: str
    ) -> str | None:
        if os.environ.get("NOVELTRAD_TRANSLATION_TEST_MODE") in {"1", "true", "yes"}:
            return f"[{target_lang}] {source}"
        if os.environ.get("NOVELTRAD_LLM_DRAFT_ON_NLLB_MISSING", "0") not in {
            "1",
            "true",
            "yes",
        }:
            return None
        prompt = (
            "Translate the following literary text faithfully. Preserve paragraph "
            "breaks and do not add commentary.\n\n"
            f"Source language: {source_lang}\n"
            f"Target language: {target_lang}\n\n"
            f"TEXT:\n{source}"
        )
        try:
            return get_router().complete(prompt, use_cache=True)
        except Exception as exc:
            logger.warning("LLM draft fallback failed: %s", exc)
            return None


__all__ = ["Worker"]

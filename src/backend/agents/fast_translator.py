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
        # In test mode, skip NLLB entirely. Loading a multi-GB model
        # synchronously at worker setup can stall the pipeline for
        # tens of seconds (the orchestrator's 90s watchdog then emits
        # "no event for 90s"). handle_task() detects a missing engine
        # and routes chunks through _fallback_translate(), which
        # honours NOVELTRAD_TRANSLATION_TEST_MODE.
        if os.environ.get("NOVELTRAD_TRANSLATION_TEST_MODE", "").lower() in {
            "1",
            "true",
            "yes",
        }:
            self._engine = None
            logger.info(
                "[%s] FastTranslator ready in translation test mode (NLLB skipped)",
                self.worker_id,
            )
            return

        # Force-load the model in setup so the first chunk doesn't pay
        # the init cost.
        engine = _get_engine()
        if not engine.available:
            # NLLB model not found or ctranslate2/sentencepiece not
            # installed.  Set _engine = None so handle_task() goes
            # straight to _fallback_translate() and tries the LLM
            # draft or falls back to NOVELTRAD_TRANSLATION_TEST_MODE.
            if engine.load_error:
                logger.warning(
                    "[%s] NLLB unavailable: %s  — chunks will use LLM draft "
                    "or identity translation fallback",
                    self.worker_id,
                    engine.load_error,
                )
            self._engine = None
            return
        self._engine = engine
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
        if self._engine is None:
            # Test mode: engine was skipped at setup(); go straight to
            # the deterministic fallback (e.g. echo source with target
            # language tag, per NOVELTRAD_TRANSLATION_TEST_MODE).
            translated = self._fallback_translate(source, src_lang, tgt_lang)
            if translated is None:
                return self._emit_error(
                    chunk_id,
                    "test_translation_unavailable",
                    "fast_translator: no translation engine available in test mode",
                )
            engine_name = "translation-test-mode"
        else:
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
        # Auto-detect LLM draft: try the LLM router directly.  This
        # works without NOVELTRAD_LLM_DRAFT_ON_NLLB_MISSING so users
        # who configured Ollama in the Settings tab get a fallback
        # immediately, even when draft_fallback is not explicitly toggled.
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
            logger.warning(
                "[%s] LLM draft fallback for chunk: %s",
                self.worker_id,
                exc,
            )
            # Last resort: explicit identity fallback when NOVELTRAD_ALLOW_IDENTITY_TRANSLATION=1
            if os.environ.get("NOVELTRAD_ALLOW_IDENTITY_TRANSLATION") in {
                "1",
                "true",
                "yes",
            }:
                logger.warning("Using explicit identity translation fallback")
                return f"[{target_lang}] {source}"
            return None


__all__ = ["Worker"]

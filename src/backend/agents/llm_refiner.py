"""LLMRefiner agent — premium-only: refines NLLB translation with LLM using source + glossary context."""

from __future__ import annotations

import logging
from typing import Any

from .base_worker import BaseWorker
from .prompt_contracts import literary_contract
from ..llm_router.router import get_router

logger = logging.getLogger(__name__)

_REFINER_PROMPT = """You are a literary translation reviser.
{contract}

Source language: {src}
Target language: {tgt}

Below is a SOURCE text, its raw machine translation, and a list of glossary
terms (source → target) that must be respected.

Your job: produce a natural, idiomatic, literary-quality translation that:
1. Is faithful to the SOURCE (no fabrication, no omission)
2. Uses the GLOSSARY TERMS correctly
3. Flows naturally in the target language (no machine-translation artifacts)
4. Preserves paragraph breaks

Return ONLY the improved translation — no commentary, no quotes, no markdown fences.

SOURCE:
{src_text}

MACHINE TRANSLATION:
{tgt_text}

GLOSSARY TERMS (source → target):
{glossary_text}

IMPROVED TRANSLATION:"""


def _format_glossary(terms: list[dict[str, Any]]) -> str:
    """Format glossary terms for the prompt."""
    if not terms:
        return "(no glossary terms provided)"
    lines = []
    for t in terms[:30]:  # limit to 30 terms
        src = (t.get("source") or "").strip()
        tgt = (t.get("target") or "").strip()
        if src and tgt and src != tgt:
            lines.append(f"{src} → {tgt}")
    return "\n".join(lines) if lines else "(no glossary terms provided)"


class Worker(BaseWorker):
    use_control_thread = True

    def setup(self) -> None:
        self._router = get_router()

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("refine",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"llm_refiner: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        src = payload.get("source_text", "")
        tgt = payload.get("glossary_applied") or payload.get("raw_translation") or ""
        terms = payload.get("lexicon_terms") or []
        src_lang = payload.get("source_lang", "en")
        tgt_lang = payload.get("target_lang", "fr")
        if not (src and tgt):
            return self._emit_error(
                chunk_id, "empty_input",
                "llm_refiner: missing source or translation"
            )
        glossary_text = _format_glossary(terms)
        prompt = _REFINER_PROMPT.format(
            contract=literary_contract(),
            src=src_lang,
            tgt=tgt_lang,
            src_text=src[:3000],
            tgt_text=tgt[:3000],
            glossary_text=glossary_text,
        )
        try:
            improved = self._router.complete(prompt)
        except Exception as exc:
            logger.warning("llm_refiner: LLM call failed: %s", exc)
            improved = tgt  # fallback to unrefined
        if not improved.strip():
            improved = tgt
        improved = improved.strip()
        # Basic guard: reject if it lost too much content
        if len(improved) < len(tgt) * 0.6 and len(tgt) >= 80:
            logger.warning("llm_refiner: rejection — too much content removed")
            improved = tgt
        return self._emit_done(
            chunk_id,
            {
                "llm_refined": improved,
                "glossary_applied": improved,  # overwrite so downstream stages use the refined version
                "status": "llm_refined",
            },
        )


__all__ = ["Worker"]

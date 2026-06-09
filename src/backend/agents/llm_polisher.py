"""LLMPolisher agent — Agent 8 of the v4 pipeline.

Reflect → Improve loop (pattern from `andrewyng/translation-agent`).

  1. TRANSLATE: the previous stage already gave us a translation.
  2. REFLECT: ask the LLM to identify weaknesses in the translation
     given the source, the previous-stage output, and the surrounding
     context (neighbour chunks). The LLM returns JSON with a list of
     `suggestions` and a free-text `reflection`.
  3. IMPROVE: ask the LLM to rewrite the translation incorporating
     the suggestions. We only keep the improvement if it is non-empty
     AND the LLM call succeeded.

The polisher uses the LLM router (Ollama or OpenAI-compatible), so
the same provider load-balancing and content-hash cache apply.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .base_worker import BaseWorker
from ..llm_router.router import get_router

logger = logging.getLogger(__name__)


_REFLECT_PROMPT = """You are a literary translation polisher.
Source language: {src}
Target language: {tgt}

Compare the SOURCE and the CURRENT TRANSLATION, considering the
SURROUNDING CONTEXT. Identify up to 5 weaknesses (style, register,
faithfulness, terminology). Return STRICT JSON:

{{"reflection": "<1-3 sentence assessment>",
 "suggestions": [
   {{"span": "<substring in the translation>",
     "issue": "<what is wrong>",
     "fix": "<a concrete improvement>"}}
 ]}}

If the translation is already good, return empty `suggestions`.

SURROUNDING CONTEXT (may be empty):
{context}

SOURCE:
{src_text}

CURRENT TRANSLATION:
{tgt_text}
"""


_IMPROVE_PROMPT = """You are a literary translation polisher.
Source language: {src}
Target language: {tgt}

Apply the following SUGGESTIONS to the CURRENT TRANSLATION, keeping
faithfulness to the SOURCE. Return the IMPROVED translation only —
no commentary, no quotes, no markdown fences.

SUGGESTIONS:
{suggestions}

SOURCE:
{src_text}

CURRENT TRANSLATION:
{tgt_text}

IMPROVED TRANSLATION:
"""


def _safe_reflection_parse(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {"reflection": "", "suggestions": []}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"reflection": "", "suggestions": []}
    if not isinstance(data, dict):
        return {"reflection": "", "suggestions": []}
    suggestions = data.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = []
    cleaned: list[dict[str, str]] = []
    for s in suggestions:
        if not isinstance(s, dict):
            continue
        cleaned.append(
            {
                "span": (s.get("span") or "").strip(),
                "issue": (s.get("issue") or "").strip(),
                "fix": (s.get("fix") or "").strip(),
            }
        )
    return {
        "reflection": (data.get("reflection") or "").strip(),
        "suggestions": cleaned,
    }


def _neighbour_context(neighbours: list[dict[str, Any]]) -> str:
    if not neighbours:
        return ""
    snippets: list[str] = []
    for n in neighbours[:2]:
        s = (n.get("source_text") or "")[:300]
        t = (
            n.get("polished_translation")
            or n.get("glossary_applied")
            or n.get("raw_translation")
            or ""
        )[:300]
        if s or t:
            snippets.append(f"---\nSRC: {s}\nTGT: {t}")
    return "\n".join(snippets)


class Worker(BaseWorker):
    use_control_thread = True

    def setup(self) -> None:
        self._router = get_router()

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("polish",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"llm_polisher: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        src = payload.get("source_text", "")
        current = (
            payload.get("grammar_checked")
            or payload.get("qa_checked")
            or payload.get("glossary_applied")
            or payload.get("raw_translation")
            or ""
        )
        neighbours = payload.get("neighbours") or []
        src_lang = payload.get("source_lang", "en")
        tgt_lang = payload.get("target_lang", "fr")
        if not (src and current):
            return self._emit_error(
                chunk_id, "empty_input", "llm_polisher: missing input"
            )

        reflect_prompt = _REFLECT_PROMPT.format(
            src=src_lang,
            tgt=tgt_lang,
            context=_neighbour_context(neighbours),
            src_text=src[:1500],
            tgt_text=current[:1500],
        )
        try:
            reflection_response = self._router.complete(reflect_prompt)
        except Exception as exc:
            logger.warning("llm_polisher: reflection failed: %s", exc)
            return self._emit_done(
                chunk_id,
                {
                    "polished_translation": current,
                    "reflection": "",
                    "suggestions": [],
                    "status": "polished",
                },
            )
        reflection = _safe_reflection_parse(reflection_response)
        suggestions = reflection.get("suggestions") or []
        if not suggestions:
            return self._emit_done(
                chunk_id,
                {
                    "polished_translation": current,
                    "reflection": reflection.get("reflection", ""),
                    "suggestions": [],
                    "status": "polished",
                },
            )

        improve_prompt = _IMPROVE_PROMPT.format(
            src=src_lang,
            tgt=tgt_lang,
            suggestions=json.dumps(suggestions, ensure_ascii=False, indent=2),
            src_text=src[:1500],
            tgt_text=current[:1500],
        )
        try:
            improved = self._router.complete(improve_prompt, use_cache=False)
        except Exception as exc:
            logger.warning("llm_polisher: improvement failed: %s", exc)
            improved = current
        if not improved.strip():
            improved = current
        return self._emit_done(
            chunk_id,
            {
                "polished_translation": improved.strip(),
                "reflection": reflection.get("reflection", ""),
                "suggestions": suggestions,
                "status": "polished",
            },
        )


__all__ = ["Worker"]

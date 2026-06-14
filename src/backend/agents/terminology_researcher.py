"""TerminologyResearcher agent — optional agent for the v4 Premium profile.

Scans chunks for named entities (proper nouns, invented terms) that
have no entry in the glossary, then queries the LLM for translation
suggestions. Outputs ``term_suggestions[]`` with source, target,
confidence, and rationale for each found entity.

Inspired by the term-researcher pattern from
``senshinji/claude-translation-skill``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .base_worker import BaseWorker
from .prompt_contracts import literary_contract
from ..llm_router.router import get_router

logger = logging.getLogger(__name__)

_RESEARCH_PROMPT = """You are a literary terminology researcher.
{contract}

Source language: {src}
Target language: {tgt}

Identify named entities, proper nouns, or invented terms in the SOURCE
text that may need special handling during translation. For each entity,
suggest a target-language rendering and explain your reasoning.

Focus on:
- Character names, place names, invented fantasy/SF terms
- Cultural references, honorifics, idioms

Return STRICT JSON:
{{
  "suggestions": [
    {{
      "source": "<the entity as it appears in the source>",
      "target": "<suggested translation or 'KEEP_AS_IS'>",
      "confidence": <float between 0.0 and 1.0>,
      "rationale": "<brief explanation>"
    }}
  ]
}}

If no entities found, return: {{"suggestions": []}}
Do not include markdown fences or commentary.

SOURCE:
{src_text}

EXISTING GLOSSARY TERMS (already handled):
{existing_terms}
"""


def _parse_suggestions(text: str) -> list[dict[str, Any]]:
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
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    suggestions = data.get("suggestions") or []
    if not isinstance(suggestions, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for s in suggestions:
        if not isinstance(s, dict):
            continue
        cleaned.append({
            "source": (s.get("source") or "").strip(),
            "target": (s.get("target") or "KEEP_AS_IS").strip(),
            "confidence": float(s.get("confidence", 0.5)),
            "rationale": (s.get("rationale") or "").strip(),
        })
    return cleaned


class Worker(BaseWorker):
    use_control_thread = True

    def setup(self) -> None:
        self._router = get_router()

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("research_terms",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"terminology_researcher: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        src = payload.get("source_text", "")
        src_lang = payload.get("source_lang", "en")
        tgt_lang = payload.get("target_lang", "fr")
        existing = payload.get("lexicon_terms") or []
        existing_str = ", ".join(
            t.get("source", "") for t in existing[:30]
        ) if existing else "(none)"

        if not src:
            return self._emit_error(
                chunk_id, "empty_input", "terminology_researcher: empty source"
            )
        prompt = _RESEARCH_PROMPT.format(
            contract=literary_contract(),
            src=src_lang,
            tgt=tgt_lang,
            src_text=src[:3000],
            existing_terms=existing_str,
        )
        try:
            response = self._router.complete(prompt)
        except Exception as exc:
            logger.warning("terminology_researcher: LLM call failed: %s", exc)
            return self._emit_done(
                chunk_id,
                {"term_suggestions": [], "status": "lexicon_ready"},
            )
        suggestions = _parse_suggestions(response)
        return self._emit_done(
            chunk_id,
            {"term_suggestions": suggestions, "status": "lexicon_ready"},
        )


__all__ = ["Worker"]

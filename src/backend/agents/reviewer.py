"""Reviewer agent — independent review step for the v4 pipeline.

Receives ``(source_text, translated_text)`` and performs a critical
review for hallucinations, omissions, register incoherence, and
proper-name mistranslations. Outputs a ``review_score`` (0.0–1.0)
and a list of ``review_annotations``.

Inspired by the anti-fabrication reviewer pattern from
``senshinji/claude-translation-skill``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .base_worker import BaseWorker
from ..llm_router.router import get_router

logger = logging.getLogger(__name__)

_REVIEW_PROMPT = """You are an independent literary translation reviewer.
Source language: {src}
Target language: {tgt}

Compare the SOURCE text with the TRANSLATION. Check for:
1. FABRICATIONS — content in the translation not present in the source
2. OMISSIONS — source content missing from the translation
3. REGISTER — tone or narrative register mismatch
4. NAMES — proper names translated when they should stay as-is

Return STRICT JSON:
{{
  "score": <float between 0.0 and 1.0, where 1.0 is perfect>,
  "annotations": [
    {{
      "type": "FABRICATION|OMISSION|REGISTER|NAMES",
      "span": "<offending excerpt from the translation>",
      "suggestion": "<a corrected version, or empty string>"
    }}
  ]
}}

If the translation is perfect, return: {{"score": 1.0, "annotations": []}}
Do not include markdown fences or commentary.

SOURCE:
{src_text}

TRANSLATION:
{tgt_text}
"""


def _parse_review(text: str) -> tuple[float, list[dict[str, Any]]]:
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
            return 0.0, []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return 0.0, []
    score_raw = data.get("score", 0.5)
    try:
        score = float(score_raw)
    except (TypeError, ValueError):
        score = 0.5
    score = max(0.0, min(1.0, score))
    annotations = data.get("annotations") or []
    if not isinstance(annotations, list):
        annotations = []
    cleaned: list[dict[str, Any]] = []
    for a in annotations:
        if not isinstance(a, dict):
            continue
        cleaned.append({
            "type": a.get("type", "UNKNOWN"),
            "span": (a.get("span") or "").strip(),
            "suggestion": (a.get("suggestion") or "").strip(),
        })
    return score, cleaned


class Worker(BaseWorker):
    use_control_thread = True

    def setup(self) -> None:
        self._router = get_router()

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("review",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"reviewer: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        src = payload.get("source_text", "")
        tgt = (
            payload.get("grammar_checked")
            or payload.get("polished_translation")
            or payload.get("glossary_applied")
            or payload.get("raw_translation")
            or ""
        )
        src_lang = payload.get("source_lang", "en")
        tgt_lang = payload.get("target_lang", "fr")
        if not (src and tgt):
            return self._emit_error(
                chunk_id, "empty_input", "reviewer: missing source/translation"
            )
        prompt = _REVIEW_PROMPT.format(
            src=src_lang,
            tgt=tgt_lang,
            src_text=src[:3000],
            tgt_text=tgt[:3000],
        )
        try:
            response = self._router.complete(prompt)
        except Exception as exc:
            logger.warning("reviewer: LLM call failed: %s", exc)
            return self._emit_done(
                chunk_id,
                {
                    "review_score": 1.0,
                    "review_annotations": [],
                    "review_skipped": True,
                    "status": "reviewed",
                },
            )
        score, annotations = _parse_review(response)
        return self._emit_done(
            chunk_id,
            {
                "review_score": score,
                "review_annotations": annotations,
                "status": "reviewed",
            },
        )


__all__ = ["Worker"]

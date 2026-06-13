"""LexiconBuilder agent — Agent 3 of the v4 pipeline.

Extracts domain-specific terminology (e.g. xianxia cultivation
terms) from a batch of translated chunks and writes lexicon entries
into the StateStore.

The LLM is asked to return strict JSON. We sanitize the response
before writing. On parse failure, the agent emits a `done` with
`status="lexicon_skipped"` so the orchestrator can move on without
a lexicon.
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


_PROMPT = """You are a terminology extractor for a literary translation.
{contract}

Given the following text in the SOURCE language and its translation in
the TARGET language, list up to 12 named entities, cultivation terms,
proper nouns, or recurring in-world concepts that MUST be translated
consistently throughout the novel.

Source language: {src}
Target language: {tgt}

Source text:
{src_text}

Translation:
{tgt_text}

Return STRICT JSON of the form:
{{"terms": [{{"source": "...", "target": "...", "category": "name|term|cultivation|place|other", "gender": "m|f|n|unknown", "confidence": 0.0}}]}}

No commentary, no markdown. JSON only.
"""


def _safe_json_parse(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # last-ditch: find the first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    terms = data.get("terms") if isinstance(data, dict) else None
    if not isinstance(terms, list):
        return []
    out: list[dict[str, Any]] = []
    for t in terms:
        if not isinstance(t, dict):
            continue
        src = (t.get("source") or "").strip()
        tgt = (t.get("target") or "").strip()
        if not src or not tgt:
            continue
        out.append(
            {
                "source": src,
                "target": tgt,
                "category": (t.get("category") or "other").strip(),
                "gender": (t.get("gender") or "unknown").strip(),
                "confidence": float(t.get("confidence", 0.5) or 0.5),
            }
        )
    return out


class Worker(BaseWorker):
    use_control_thread = True

    def setup(self) -> None:
        self._router = get_router()

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("build_lexicon",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"lexicon_builder: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        src = payload.get("source_text", "")
        tgt = payload.get("raw_translation", "")
        src_lang = payload.get("source_lang", "en")
        tgt_lang = payload.get("target_lang", "fr")
        if not (src and tgt):
            return self._emit_done(
                chunk_id, {"status": "lexicon_skipped", "terms": []}
            )
        prompt = _PROMPT.format(
            contract=literary_contract(),
            src=src_lang,
            tgt=tgt_lang,
            src_text=src[:1500],
            tgt_text=tgt[:1500],
        )
        try:
            response = self._router.complete(prompt)
        except Exception as exc:
            logger.warning("lexicon_builder: LLM call failed: %s", exc)
            return self._emit_done(
                chunk_id, {"status": "lexicon_skipped", "terms": []}
            )
        terms = _safe_json_parse(response)
        for t in terms:
            import uuid

            t.setdefault("id", uuid.uuid4().hex[:12])
            t.setdefault("aliases", [])
            t.setdefault("notes", "")
            t.setdefault("validated_by_user", False)
            t.setdefault("chapter_id", payload.get("chapter_id"))
        return self._emit_done(
            chunk_id,
            {
                "status": "lexicon_ready",
                "terms": terms,
            },
        )


__all__ = ["Worker"]

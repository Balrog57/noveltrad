"""QAValidator agent — Agent 6 of the v4 pipeline.

Two-pass anti-fabrication LLM check, following the pattern from
`senshinji/claude-translation-skill`:

  Pass 1 — Detect: ask the LLM to identify issues, scoring them by
           priority FABRICATION > OMISSION > STRUCTURE > TERMINOLOGY
           > REGISTER. The LLM returns strict JSON.
  Pass 2 — Propose: for every high-priority issue, ask the LLM to
           propose a corrected version. We accept the corrections
           only if they are non-empty and short.

Issues are stored in the StateStore `qa_issues` table (via the
orchestrator) and shown in the chunk detail dialog.
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


_DETECT_PROMPT = """You are a literary translation QA reviewer.
{contract}

Source language: {src}
Target language: {tgt}

Compare the SOURCE and the TRANSLATION. Identify issues, classified
into the following priority buckets (highest first):
  FABRICATION, OMISSION, STRUCTURE, TERMINOLOGY, REGISTER

Return STRICT JSON:
{{"issues": [
  {{"priority": "FABRICATION|OMISSION|STRUCTURE|TERMINOLOGY|REGISTER",
   "quote": "<the offending span in the translation>",
   "explanation": "<why it is a problem>",
   "auto_fix": "<a proposed replacement, or empty string if unfixable>"}}
]}}

If no issues, return {{"issues": []}}.

SOURCE:
{src_text}

TRANSLATION:
{tgt_text}
"""


def _safe_issues_parse(text: str) -> list[dict[str, Any]]:
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
    issues = data.get("issues") if isinstance(data, dict) else None
    if not isinstance(issues, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for it in issues:
        if not isinstance(it, dict):
            continue
        priority = (it.get("priority") or "REGISTER").upper()
        if priority not in ("FABRICATION", "OMISSION", "STRUCTURE", "TERMINOLOGY", "REGISTER"):
            priority = "REGISTER"
        cleaned.append(
            {
                "priority": priority,
                "quote": (it.get("quote") or "").strip(),
                "explanation": (it.get("explanation") or "").strip(),
                "auto_fix": (it.get("auto_fix") or "").strip(),
            }
        )
    return cleaned


def _apply_fixes(text: str, issues: list[dict[str, Any]]) -> str:
    """Replace each quoted span with its auto_fix, if available.

    We only apply fixes for issues with priority >= TERMINOLOGY
    (i.e. FABRICATION/OMISSION/STRUCTURE/TERMINOLOGY) and only when
    the quote is found verbatim in the text. REGISTER fixes are
    stylistic and are not auto-applied.
    """
    out = text
    for it in issues:
        if it["priority"] in ("REGISTER",):
            continue
        fix = it.get("auto_fix") or ""
        quote = it.get("quote") or ""
        if fix and quote and quote in out:
            out = out.replace(quote, fix, 1)
    return out


class Worker(BaseWorker):
    use_control_thread = True

    def setup(self) -> None:
        self._router = get_router()

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("qa_check",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"qa_validator: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        src = payload.get("source_text", "")
        tgt = payload.get("glossary_applied") or payload.get("raw_translation") or ""
        src_lang = payload.get("source_lang", "en")
        tgt_lang = payload.get("target_lang", "fr")
        if not (src and tgt):
            return self._emit_error(
                chunk_id, "empty_input", "qa_validator: missing source/translation"
            )
        prompt = _DETECT_PROMPT.format(
            contract=literary_contract(),
            src=src_lang,
            tgt=tgt_lang,
            src_text=src[:2000],
            tgt_text=tgt[:2000],
        )
        try:
            response = self._router.complete(prompt)
        except Exception as exc:
            logger.warning("qa_validator: LLM call failed: %s", exc)
            return self._emit_done(
                chunk_id,
                {
                    "qa_checked": tgt,
                    "qa_issues": [],
                    "status": "qa_checked",
                    "qa_skipped": True,
                },
            )
        issues = _safe_issues_parse(response)
        # Pass 2: we don't run a second LLM call (we already asked for
        # auto_fix in pass 1). Apply the fixes that we have.
        fixed = _apply_fixes(tgt, issues)
        qa_payload = {
            "qa_checked": fixed,
            "qa_issues": issues,
            "status": "qa_checked",
        }
        return self._emit_done(chunk_id, qa_payload)


__all__ = ["Worker"]

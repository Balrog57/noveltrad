"""GlossaryApplier agent — Agent 4 of the v4 pipeline.

Applies the project lexicon to the raw translation: replaces each
source term by the canonical target translation. This is a purely
deterministic step; no LLM call. The result is a `glossary_applied`
text that the next stage (ConsistencyChecker) can also use as a
reference.

The agent reads the lexicon from the task payload (pre-fetched by the
orchestrator) — the StateStore is the single writer and the agent
does not touch it directly.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .base_worker import BaseWorker

logger = logging.getLogger(__name__)


def _apply_glossary(text: str, terms: list[dict[str, Any]]) -> tuple[str, int]:
    """Apply source->target substitutions, longest-source-first."""
    if not text or not terms:
        return text, 0
    pairs: list[tuple[str, str]] = []
    for t in terms:
        src = (t.get("source") or "").strip()
        tgt = (t.get("target") or "").strip()
        if not src or not tgt or src == tgt:
            continue
        pairs.append((src, tgt))
        for alias in t.get("aliases") or []:
            a = (alias or "").strip()
            if a:
                pairs.append((a, tgt))
    if not pairs:
        return text, 0
    pairs.sort(key=lambda p: -len(p[0]))
    pattern = "|".join(re.escape(s) for s, _ in pairs)
    replacement_map = dict(pairs)
    count = 0

    def _sub(m: re.Match[str]) -> str:
        nonlocal count
        src = m.group(0)
        tgt = replacement_map.get(src, src)
        if tgt != src:
            count += 1
        return tgt

    out = re.sub(pattern, _sub, text)
    return out, count


class Worker(BaseWorker):
    use_control_thread = True

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("apply_glossary",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"glossary_applier: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        raw = payload.get("raw_translation") or ""
        terms = payload.get("lexicon_terms") or []
        if not raw:
            return self._emit_error(
                chunk_id, "empty_translation", "glossary_applier: no raw translation"
            )
        try:
            applied, n = _apply_glossary(raw, terms)
        except Exception as exc:
            return self._emit_error(
                chunk_id, "glossary_failed", f"glossary_applier: {exc}"
            )
        return self._emit_done(
            chunk_id,
            {
                "glossary_applied": applied,
                "glossary_substitutions": n,
                "status": "glossary_applied",
            },
        )


__all__ = ["Worker", "_apply_glossary"]

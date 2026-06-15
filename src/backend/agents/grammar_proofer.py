"""GrammarProofer agent — Agent 7 of the v4 pipeline.

Runs a grammar/spelling pass on the QA-validated translation. We
support two backends:

  * language_tool_python (works for English/French/German/Spanish/…)
  * pygrammalecte (French only, more thorough)

Both are optional. If neither is installed, the agent becomes a
pass-through and emits the QA output unchanged. Grammar issues are
persisted to `grammar_issues` by the orchestrator.
"""

from __future__ import annotations

import logging
from typing import Any

from .base_worker import BaseWorker

logger = logging.getLogger(__name__)


class Worker(BaseWorker):
    use_control_thread = True

    def setup(self) -> None:
        self._lt = None
        self._grammalecte = None
        try:
            import language_tool_python  # type: ignore

            self._lt = language_tool_python.LanguageTool("auto")
        except Exception:
            self._lt = None
        try:
            import pygrammalecte  # type: ignore

            self._grammalecte = pygrammalecte.GrammarChecker()
        except Exception:
            self._grammalecte = None
        logger.info(
            "[%s] GrammarProofer ready (language_tool=%s, grammalecte=%s)",
            self.worker_id,
            self._lt is not None,
            self._grammalecte is not None,
        )

    def teardown(self) -> None:
        if self._lt is not None:
            try:
                self._lt.close()
            except Exception:
                pass

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        action = msg.get("action")
        if action not in ("proofread",):
            return self._emit_error(
                msg.get("chunk_id"),
                "unknown_action",
                f"grammar_proofer: unknown action {action!r}",
            )
        payload = msg.get("payload") or {}
        chunk_id = msg.get("chunk_id")
        text = (
            payload.get("qa_checked")
            or payload.get("glossary_applied")
            or payload.get("raw_translation")
            or ""
        )
        if not text:
            return self._emit_error(
                chunk_id, "empty_input", "grammar_proofer: empty text"
            )

        issues: list[dict[str, Any]] = []
        corrected = text
        if self._lt is not None:
            try:
                matches = self._lt.check(text)
            except Exception as exc:
                logger.warning("grammar_proofer: language_tool failed: %s", exc)
                matches = []
            for m in matches:
                if not m.replacements:
                    continue
                replacement = m.replacements[0]
                if not replacement:
                    continue
                issues.append(
                    {
                        "start_pos": m.offset,
                        "end_pos": m.offset + m.errorLength,
                        "message": m.message,
                        "suggestion": replacement,
                        "rule_id": getattr(m, "ruleId", None) or m.rule.id,
                    }
                )
                start = m.offset
                end = m.offset + m.errorLength
                corrected = corrected[:start] + replacement + corrected[end:]
        # Grammalecte — French-specific grammar pass
        # Runs after language_tool for deeper French grammar checking.
        if self._grammalecte is not None and msg.get("target_lang", "fr") == "fr":
            try:
                from pygrammalecte import grammalecte_text
                for gm in grammalecte_text(corrected):
                    issues.append(
                        {
                            "start_pos": gm.start,
                            "end_pos": gm.end,
                            "message": gm.message,
                            "suggestion": gm.suggestions[0] if gm.suggestions else "",
                            "rule_id": gm.rule,
                        }
                    )
                    if gm.suggestions:
                        corrected = (
                            corrected[: gm.start]
                            + gm.suggestions[0]
                            + corrected[gm.end :]
                        )
            except Exception as exc:
                logger.warning("grammar_proofer: grammalecte failed: %s", exc)

        return self._emit_done(
            chunk_id,
            {
                "grammar_checked": corrected,
                "grammar_issues": issues,
                "status": "grammar_checked",
            },
        )


__all__ = ["Worker"]

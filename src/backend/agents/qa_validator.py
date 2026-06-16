"""QAValidator agent — Agent 6 of the v4 pipeline.

Two-pass reflect-improve LLM check, following the pattern from
`andrewyng/translation-agent`:

  Pass 1 — Detect: ask the LLM to identify issues, scoring them by
           priority FABRICATION > OMISSION > STRUCTURE > TERMINOLOGY
           > REGISTER. The LLM returns strict JSON.
  Pass 2 — Improve: for every detected high-priority issue, ask the
           LLM to produce an improved translation that addresses the
           issues. We fall back to auto_fix replacements only if the
           improvement call fails.

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
{tgt_text}"""


_IMPROVE_PROMPT = """You are a literary translation QA reviser.
{contract}

Source language: {src}
Target language: {tgt}

The following ISSUES were detected in the CURRENT TRANSLATION.
Revise the translation to fix ALL of the listed issues while keeping
faithfulness to the SOURCE. Return ONLY the corrected translation —
no commentary, no quotes, no markdown fences.

ISSUES:
{issues}

SOURCE:
{src_text}

CURRENT TRANSLATION:
{tgt_text}

CORRECTED TRANSLATION:"""


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


def _issues_text(issues: list[dict[str, Any]]) -> str:
    """Format issues as a bullet-list text for the improve prompt."""
    lines: list[str] = []
    for i, it in enumerate(issues, 1):
        priority = it.get("priority", "REGISTER")
        quote = it.get("quote", "")
        explanation = it.get("explanation", "")
        fix = it.get("auto_fix", "")
        if not quote and not explanation:
            continue
        line = f"{i}. [{priority}]"
        if quote:
            line += f" \"{quote}\""
        if explanation:
            line += f" — {explanation}"
        if fix:
            line += f" | Suggested fix: {fix}"
        lines.append(line)
    return "\n".join(lines)


def _source_leak_count(source: str, translation: str) -> int:
    """Count meaningful source words that appear verbatim in the translation.

    Excludes common short words (in, of, the…) and genre-specific terms
    (xianxia cultivation, technical vocabulary, common cognates) that are
    legitimate in both source and target languages.
    """
    import re as _re

    _WHITELISTED_LEXICON = frozenset(
        {
            # Xianxia / cultivation terms (legitimate in FR)
            "qi", "dao", "yin", "yang", "dantian",
            "meridian", "meridians", "cultivation", "cultivator", "cultivators",
            "sect", "sects", "jade", "alchemy", "spirit", "spiritual",
            "pill", "pills", "elixir", "elixirs", "heaven", "earth",
            "mortal", "immortal", "immortals", "realm", "realms",
            "soul", "souls", "demon", "demons", "divine", "phoenix",
            "dragon", "beast", "beasts", "refining", "array", "arrays",
            "talisman", "artefact", "artefacts", "artifact", "artifacts",
            "master", "elder", "elders", "disciple", "disciples",
            "senior", "junior", "ancestor", "ancestors", "patriarch",
            "sword", "blade", "treasure", "treasures", "technique", "techniques",
            "scripture", "scriptures", "manual", "manuals",
            "breakthrough", "foundation", "core", "nascent",
            "tribulation", "lightning", "lotus", "bamboo",
            # Technical / domain terms
            "api", "json", "http", "https", "rest", "cli", "gui",
            "sql", "html", "css", "xml", "yaml", "toml",
            "url", "uri", "uuid", "sha", "hash", "token", "oauth",
            "jwt", "base64", "utf", "ascii", "unicode",
            "config", "debug", "cache", "proxy", "socket",
            "thread", "process", "daemon", "schema", "metadata",
            "payload", "endpoint", "callback", "middleware",
            "module", "package", "dependency", "repository",
            "binary", "boolean", "integer", "buffer", "cluster",
            "container", "docker",
            # Common English/French cognates that are legitimate in FR
            "possible", "probable", "nature", "culture",
            "structure", "architecture",
            "histoire", "musique", "pratique", "politique", "critique",
            "unique", "authentique", "dynamique", "logique",
            "magique", "tragique", "comique", "public",
            "anglais", "francais", "français", "chinois", "japonais",
        }
    )
    _EXCLUDED_WORDS = frozenset({
        "this", "that", "with", "from", "into", "your",
        "have", "were", "been", "they", "them",
    })
    source_words = {
        w.lower()
        for w in _re.findall(r"[A-Za-z][A-Za-z'-]{3,}", source)
        if w.lower() not in _EXCLUDED_WORDS
        and w.lower() not in _WHITELISTED_LEXICON
    }
    if not source_words:
        return 0
    translated_words = {
        w.lower() for w in _re.findall(r"[A-Za-z][A-Za-z'-]{3,}", translation)
    }
    return len(source_words & translated_words)


def _rejects_as_source_leak(source: str, current: str, improved: str) -> bool:
    """Reject a fix that leaks source-language words more than its input."""
    current_leaks = _source_leak_count(source, current)
    improved_leaks = _source_leak_count(source, improved)
    return improved_leaks >= 2 and improved_leaks > current_leaks + 1


def _paragraph_count(text: str) -> int:
    return len([p for p in re.split(r"\n\s*\n+", text.strip()) if p.strip()])


def _rejects_as_assistant_reply(current: str, improved: str) -> bool:
    """Reject chatty LLM replies instead of translation-only output."""
    lowered = improved.strip().lower()
    bad_prefixes = (
        "bien sûr",
        "voici",
        "traduction",
        "traduction améliorée",
        "traduction corrigée",
        "sure",
        "certainly",
        "here is",
        "here's",
        "improved translation",
        "corrected translation",
        "voici la traduction",
    )
    if lowered.startswith(bad_prefixes):
        return True
    first_line = lowered.splitlines()[0] if lowered else ""
    if "traduction" in first_line and ":" in first_line:
        return True
    current_paragraphs = _paragraph_count(current)
    improved_paragraphs = _paragraph_count(improved)
    return current_paragraphs > 0 and improved_paragraphs > current_paragraphs + 1


def _rejects_as_omission(current: str, improved: str) -> bool:
    """Reject a fix that likely drops translated content."""
    current_paragraphs = _paragraph_count(current)
    improved_paragraphs = _paragraph_count(improved)
    if current_paragraphs > 0 and improved_paragraphs < current_paragraphs:
        return True
    current_len = len(current.strip())
    improved_len = len(improved.strip())
    return current_len >= 80 and improved_len < int(current_len * 0.65)


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

        # ---- Pass 1: Detect issues ----
        detect_prompt = _DETECT_PROMPT.format(
            contract=literary_contract(),
            src=src_lang,
            tgt=tgt_lang,
            src_text=src[:2000],
            tgt_text=tgt[:2000],
        )
        try:
            detect_response = self._router.complete(detect_prompt)
        except Exception as exc:
            logger.warning("qa_validator: detection LLM call failed: %s", exc)
            return self._emit_done(
                chunk_id,
                {
                    "qa_checked": tgt,
                    "qa_issues": [],
                    "status": "qa_checked",
                    "qa_skipped": True,
                },
            )

        issues = _safe_issues_parse(detect_response)

        # No issues found — pass through as-is
        if not issues:
            return self._emit_done(
                chunk_id,
                {
                    "qa_checked": tgt,
                    "qa_issues": [],
                    "status": "qa_checked",
                },
            )

        # ---- Pass 2: Improve (LLM-driven correction) ----
        # Only send high-priority issues (FABRICATION, OMISSION, STRUCTURE, TERMINOLOGY)
        # to the improve pass. REGISTER issues are stylistic and handled by follow-up stages.
        high_priority_issues = [
            it for it in issues
            if it["priority"] in ("FABRICATION", "OMISSION", "STRUCTURE", "TERMINOLOGY")
        ]

        if high_priority_issues:
            issues_formatted = _issues_text(high_priority_issues)
            improve_prompt = _IMPROVE_PROMPT.format(
                contract=literary_contract(),
                src=src_lang,
                tgt=tgt_lang,
                issues=issues_formatted,
                src_text=src[:1500],
                tgt_text=tgt[:1500],
            )
            try:
                improved = self._router.complete(improve_prompt, use_cache=False)
            except Exception as exc:
                logger.warning(
                    "qa_validator: improvement LLM call failed, falling back to auto_fix: %s",
                    exc,
                )
                improved = ""

            if improved and improved.strip():
                improved = improved.strip()

                # Apply guard rails (same pattern as llm_polisher)
                if _rejects_as_source_leak(src, tgt, improved):
                    logger.warning("qa_validator: source-leak rejection")
                    improved = ""
                elif _rejects_as_assistant_reply(tgt, improved):
                    logger.warning("qa_validator: assistant-reply rejection")
                    improved = ""
                elif _rejects_as_omission(tgt, improved):
                    logger.warning("qa_validator: omission rejection")
                    improved = ""

        # If improvement produced nothing usable, fall back to auto_fix replacements
        if not improved or not improved.strip():
            fixed = _apply_fixes(tgt, issues)
        else:
            fixed = improved

        return self._emit_done(
            chunk_id,
            {
                "qa_checked": fixed,
                "qa_issues": issues,
                "status": "qa_checked",
            },
        )


__all__ = ["Worker"]

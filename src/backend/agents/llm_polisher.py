"""LLMPolisher agent — Agent 8 of the v4 pipeline.

Multi-pass Reflect → Improve loop (pattern from `andrewyng/translation-agent`).

  1. TRANSLATE: the previous stage already gave us a translation.
  2. REFLECT (pass 1): ask the LLM to identify weaknesses in the translation
     given the source, the previous-stage output, and the surrounding
     context (neighbour chunks). The LLM returns JSON with a list of
     `suggestions` and a free-text `reflection`.
  3. IMPROVE (pass 1): ask the LLM to rewrite the translation incorporating
     the suggestions. We only keep the improvement if it is non-empty
     AND the LLM call succeeded.
  4. REFLECT (pass 2): if the first pass made a change, reflect again on the
     improved version. Only suggest remaining issues that were NOT fixed.
  5. IMPROVE (pass 2): apply second-round suggestions, with same rejection guards.

The polisher uses the LLM router (Ollama or OpenAI-compatible), so
the same provider load-balancing and content-hash cache apply.

Configurable via env var:
  NOVELTRAD_MAX_REFLECTION_PASSES=2   (default 2, max 3)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from .base_worker import BaseWorker
from .prompt_contracts import literary_contract
from ..llm_router.router import get_router

logger = logging.getLogger(__name__)

# Max reflection-improvement passes (env override for testing)
_MAX_PASSES = max(1, min(3, int(os.environ.get("NOVELTRAD_MAX_REFLECTION_PASSES", "2"))))


_REFLECT_PROMPT = """You are a literary translation polisher.
{contract}

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
{tgt_text}"""


_IMPROVE_PROMPT = """You are a literary translation polisher.
{contract}

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

IMPROVED TRANSLATION:"""


_REFLECT_PASS2_PROMPT = """You are a literary translation polisher — second review pass.
{contract}

Source language: {src}
Target language: {tgt}

This translation was already improved once based on earlier suggestions.
Review the CURRENT (already improved) translation against the SOURCE.

If it is now good enough, return {{"reflection": "Good.", "suggestions": []}}.

If you still see remaining weaknesses (style, register, faithfulness,
terminology issues that were NOT fixed in the first pass), return up to
3 suggestions with {{"reflection": "<assessment>", "suggestions": [...]}}.
Focus only on issues that are still visible — do not repeat old suggestions
that were already addressed.

SURROUNDING CONTEXT (may be empty):
{context}

SOURCE:
{src_text}

IMPROVED TRANSLATION:
{tgt_text}"""


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


# Technical and xianxia terms that are legitimate in both source and target.
# These should never count as "source leaks" in EN→FR translation.
_WHITELISTED_LEXICON = frozenset(
    {
        # Xianxia / cultivation terms (legitimate in FR)
        "qi",
        "dao",
        "yin",
        "yang",
        "dantian",
        "meridian",
        "meridians",
        "cultivation",
        "cultivator",
        "cultivators",
        "sect",
        "sects",
        "jade",
        "alchemy",
        "spirit",
        "spiritual",
        "pill",
        "pills",
        "elixir",
        "elixirs",
        "heaven",
        "earth",
        "mortal",
        "immortal",
        "immortals",
        "realm",
        "realms",
        "soul",
        "souls",
        "demon",
        "demons",
        "divine",
        "phoenix",
        "dragon",
        "beast",
        "beasts",
        "refining",
        "array",
        "arrays",
        "talisman",
        "artefact",
        "artefacts",
        "artifact",
        "artifacts",
        "master",
        "elder",
        "elders",
        "disciple",
        "disciples",
        "senior",
        "junior",
        "ancestor",
        "ancestors",
        "patriarch",
        "sword",
        "blade",
        "treasure",
        "treasures",
        "technique",
        "techniques",
        "scripture",
        "scriptures",
        "manual",
        "manuals",
        "breakthrough",
        "foundation",
        "core",
        "nascent",
        "tribulation",
        "lightning",
        "lotus",
        "bamboo",
        # Technical / domain terms
        "api",
        "json",
        "http",
        "https",
        "rest",
        "cli",
        "gui",
        "sql",
        "html",
        "css",
        "xml",
        "yaml",
        "toml",
        "url",
        "uri",
        "uuid",
        "sha",
        "hash",
        "token",
        "oauth",
        "jwt",
        "base64",
        "utf",
        "ascii",
        "unicode",
        "config",
        "debug",
        "cache",
        "proxy",
        "socket",
        "thread",
        "process",
        "daemon",
        "schema",
        "metadata",
        "payload",
        "endpoint",
        "callback",
        "middleware",
        "module",
        "package",
        "dependency",
        "repository",
        "binary",
        "boolean",
        "integer",
        "buffer",
        "cluster",
        "container",
        "docker",
        # Common English/French cognates that are legitimate in FR
        "possible",
        "probable",
        "nature",
        "culture",
        "structure",
        "architecture",
        "histoire",
        "musique",
        "pratique",
        "politique",
        "critique",
        "unique",
        "authentique",
        "dynamique",
        "logique",
        "magique",
        "tragique",
        "comique",
        "public",
        "anglais",
        "francais",
        "français",
        "chinois",
        "japonais",
    }
)


def _source_leak_count(source: str, translation: str) -> int:
    """Count meaningful source words that appear verbatim in the translation.

    Excludes common short words (in, of, the…) and genre-specific terms
    (xianxia cultivation, technical vocabulary, common cognates) that are
    legitimate in both source and target languages.
    """
    source_words = {
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", source)
        if w.lower()
        not in {
            "this",
            "that",
            "with",
            "from",
            "into",
            "your",
            "have",
            "were",
            "been",
            "they",
            "them",
        }
        and w.lower() not in _WHITELISTED_LEXICON
    }
    if not source_words:
        return 0
    translated_words = {
        w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", translation)
    }
    return len(source_words & translated_words)


def _rejects_as_source_leak(source: str, current: str, improved: str) -> bool:
    """Reject a polish that leaks source-language words more than its input."""
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
        "sure",
        "certainly",
        "here is",
        "here's",
        "improved translation",
        "the improved translation",
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
    """Reject a polish that likely drops translated content."""
    current_paragraphs = _paragraph_count(current)
    improved_paragraphs = _paragraph_count(improved)
    if current_paragraphs > 0 and improved_paragraphs < current_paragraphs:
        return True
    current_len = len(current.strip())
    improved_len = len(improved.strip())
    return current_len >= 80 and improved_len < int(current_len * 0.65)


def _run_reflect_improve_pass(
    router: Any,
    src: str,
    current: str,
    src_lang: str,
    tgt_lang: str,
    neighbours: list[dict[str, Any]],
    pass_num: int,
    prev_suggestions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run one reflect→improve pass. Returns result dict with keys:
    translation, reflection, suggestions, changed, passes.
    """
    if pass_num == 1:
        prompt = _REFLECT_PROMPT.format(
            contract=literary_contract(),
            src=src_lang,
            tgt=tgt_lang,
            context=_neighbour_context(neighbours),
            src_text=src[:1500],
            tgt_text=current[:1500],
        )
    else:
        prompt = _REFLECT_PASS2_PROMPT.format(
            contract=literary_contract(),
            src=src_lang,
            tgt=tgt_lang,
            context=_neighbour_context(neighbours),
            src_text=src[:1500],
            tgt_text=current[:1500],
        )

    try:
        reflection_response = router.complete(prompt)
    except Exception as exc:
        logger.warning("llm_polisher: pass %d reflection failed: %s", pass_num, exc)
        return {
            "translation": current,
            "reflection": "",
            "suggestions": [],
            "changed": False,
            "passes": 0,
        }

    reflection = _safe_reflection_parse(reflection_response)
    suggestions = reflection.get("suggestions") or []

    # If no suggestions, we're done with this pass
    if not suggestions:
        return {
            "translation": current,
            "reflection": reflection.get("reflection", ""),
            "suggestions": [],
            "changed": False,
            "passes": 0,
        }

    # On pass 2, check if suggestions are genuinely new — skip if same as pass 1
    if pass_num > 1 and prev_suggestions:
        prev_issues = {s.get("issue", "") for s in prev_suggestions if isinstance(s, dict)}
        new_issues = {s.get("issue", "") for s in suggestions if isinstance(s, dict)}
        if new_issues.issubset(prev_issues) and len(new_issues) <= len(prev_issues):
            logger.debug("llm_polisher: pass %d suggestions redundant, skipping", pass_num)
            return {
                "translation": current,
                "reflection": reflection.get("reflection", ""),
                "suggestions": suggestions,
                "changed": False,
                "passes": 0,
            }

    improve_prompt = _IMPROVE_PROMPT.format(
        contract=literary_contract(),
        src=src_lang,
        tgt=tgt_lang,
        suggestions=json.dumps(suggestions, ensure_ascii=False, indent=2),
        src_text=src[:1500],
        tgt_text=current[:1500],
    )
    try:
        improved = router.complete(improve_prompt, use_cache=False)
    except Exception as exc:
        logger.warning("llm_polisher: pass %d improvement failed: %s", pass_num, exc)
        improved = current

    if not improved.strip():
        improved = current
    improved = improved.strip()
    changed = False

    if _rejects_as_source_leak(src, current, improved):
        logger.warning(
            "llm_polisher: pass %d source-leak rejection (chunk)", pass_num
        )
    elif _rejects_as_assistant_reply(current, improved):
        logger.warning(
            "llm_polisher: pass %d assistant-reply rejection (chunk)", pass_num
        )
    elif _rejects_as_omission(current, improved):
        logger.warning(
            "llm_polisher: pass %d omission rejection (chunk)", pass_num
        )
    else:
        changed = improved != current

    return {
        "translation": improved if changed else current,
        "reflection": reflection.get("reflection", ""),
        "suggestions": suggestions,
        "changed": changed,
        "passes": 1,
    }


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
            payload.get("polished_translation")
            or payload.get("grammar_checked")
            or payload.get("qa_checked")
            or payload.get("glossary_applied")
            or payload.get("raw_translation")
            or ""
        )
        # Reflection instructions from reviewer take precedence over plain polish.
        reflection_instructions = payload.get("reflection_instructions")
        review_score = payload.get("review_score")
        review_annotations = payload.get("review_annotations") or []
        neighbours = payload.get("neighbours") or []
        src_lang = payload.get("source_lang", "en")
        tgt_lang = payload.get("target_lang", "fr")
        if not (src and current):
            return self._emit_error(
                chunk_id, "empty_input", "llm_polisher: missing input"
            )

        # When the orchestrator sends a reflection task (from reviewer),
        # use a focused one-shot rewrite instead of the multi-pass loop.
        if reflection_instructions:
            return self._polish_with_reflection(
                chunk_id,
                src,
                current,
                reflection_instructions,
                review_score,
                review_annotations,
                src_lang,
                tgt_lang,
            )

        # ---- Multi-pass boucle réflexive ----
        best = current
        all_suggestions: list[dict[str, Any]] = []
        all_reflections: list[str] = []
        total_passes = 0

        for pass_num in range(1, _MAX_PASSES + 1):
            result = _run_reflect_improve_pass(
                self._router,
                src,
                best,
                src_lang,
                tgt_lang,
                neighbours,
                pass_num,
                all_suggestions,
            )
            total_passes += result["passes"]
            if result["changed"]:
                best = result["translation"]
                all_reflections.append(result["reflection"])
                all_suggestions.extend(result["suggestions"])
                # Stop if the second pass didn't further improve
                if pass_num >= 2:
                    logger.info(
                        "llm_polisher: multi-pass completed after %d pass(es)",
                        pass_num,
                    )
                    break
            else:
                # No change in this pass — stop
                if result["reflection"]:
                    all_reflections.append(result["reflection"])
                break

        logger.debug(
            "llm_polisher: chunk=%s passes=%d changed=%s",
            chunk_id,
            total_passes,
            best != current,
        )

        return self._emit_done(
            chunk_id,
            {
                "polished_translation": best,
                "reflection": " | ".join(
                    r for r in all_reflections if r
                ) if all_reflections else "",
                "suggestions": all_suggestions,
                "reflection_passes": total_passes,
                "status": "polished",
            },
        )

    def _polish_with_reflection(
        self,
        chunk_id: str | None,
        src: str,
        current: str,
        reflection_instructions: str,
        review_score: float | None,
        review_annotations: list[dict[str, Any]],
        src_lang: str,
        tgt_lang: str,
    ) -> dict[str, Any] | None:
        """One-shot revision driven by reviewer annotations (no multi-pass)."""
        annot_text = (
            "\n".join(
                f"- [{a.get('type', '')}] {a.get('span', '')}: {a.get('suggestion', '')}"
                for a in review_annotations[:5]
            )
            if review_annotations
            else ""
        )
        prompt = _REFLECTION_REWRITE_PROMPT.format(
            contract=literary_contract(),
            src=src_lang,
            tgt=tgt_lang,
            instructions=reflection_instructions,
            annotations=annot_text,
            src_text=src[:1500],
            tgt_text=current[:1500],
        )
        try:
            improved = self._router.complete(prompt, use_cache=False)
        except Exception as exc:
            logger.warning("llm_polisher: reflection rewrite failed: %s", exc)
            improved = current
        if not improved.strip():
            improved = current
        improved = improved.strip()
        if _rejects_as_source_leak(src, current, improved):
            improved = current
        elif _rejects_as_assistant_reply(current, improved):
            improved = current
        elif _rejects_as_omission(current, improved):
            improved = current
        return self._emit_done(
            chunk_id,
            {
                "polished_translation": improved,
                "reflection": reflection_instructions,
                "suggestions": review_annotations,
                "review_score": review_score,
                "reflection_passes": 0,
                "status": "polished",
            },
        )


_REFLECTION_REWRITE_PROMPT = """You are a literary translation reviser.
{contract}

Source language: {src}
Target language: {tgt}

A previous reviewer evaluated the CURRENT TRANSLATION and gave it a low score.
Apply the following INSTRUCTIONS and ANNOTATIONS to produce an IMPROVED
TRANSLATION. Preserve all source content, fix only the identified issues,
and do not add commentary or markdown fences.

INSTRUCTIONS:
{instructions}

ANNOTATIONS:
{annotations}

SOURCE:
{src_text}

CURRENT TRANSLATION:
{tgt_text}

IMPROVED TRANSLATION:"""


__all__ = ["Worker"]

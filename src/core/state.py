"""Translation pipeline state (TypedDict).

Faithful to CDC §2 (src/core/state.py). This dict flows through the LangGraph
StateGraph as the single shared state between the 4 agent nodes.
"""

from __future__ import annotations

from typing import Any, TypedDict


class TranslationState(TypedDict, total=False):
    # Entrées
    source_text: str
    source_lang: str
    target_lang: str
    tone: str
    glossary: dict[str, str]

    # Sorties intermédiaires des agents
    draft_translation: str | None
    corrected_text: str | None
    edits_made: list[dict[str, Any]] | None
    glossary_applied_text: str | None
    glossary_matches: list[dict[str, Any]] | None

    # Sortie finale & validation
    final_text: str | None
    fidelity_score: int | None
    status: str | None
    flags: list[dict[str, Any]] | None

    # Utilisé pour alimenter l'inspecteur UI (CoT / logs par agent)
    logs: list[str]


def make_initial_state(
    source_text: str,
    source_lang: str,
    target_lang: str,
    tone: str = "Professional",
    glossary: dict[str, str] | None = None,
) -> TranslationState:
    """Build a fresh TranslationState ready to be streamed through the graph."""
    return TranslationState(
        source_text=source_text,
        source_lang=source_lang,
        target_lang=target_lang,
        tone=tone,
        glossary=glossary or {},
        draft_translation=None,
        corrected_text=None,
        edits_made=None,
        glossary_applied_text=None,
        glossary_matches=None,
        final_text=None,
        fidelity_score=None,
        status=None,
        flags=None,
        logs=[],
    )

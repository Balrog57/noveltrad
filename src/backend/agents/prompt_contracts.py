"""Shared literary prompt contracts for LLM-backed agents.

This module is backend-only and deliberately GUI-free. It keeps the
translation invariants in one place so extractor, reviewer, QA, and
polisher prompts do not drift apart.
"""

from __future__ import annotations


LITERARY_TRANSLATION_CONTRACT = """Shared literary translation contract:
- Preserve proper names unless a validated glossary entry says otherwise.
- Preserve dialogue attribution, paragraph order, and narrative point of view.
- Do not add events, motivations, lore, facts, or hallucinations absent from the source.
- Do not omit source meaning, including short beats, gestures, honorifics, or repeated names.
- Keep the target register consistent with the source register and genre.
- Respect imposed glossary choices, aliases, transliteration, and in-world terminology.
- For fantasy/SF terms, prefer stable transliteration or KEEP_AS_IS when unsure.
"""


def literary_contract() -> str:
    """Return the shared contract text for prompt interpolation."""
    return LITERARY_TRANSLATION_CONTRACT.strip()


__all__ = ["LITERARY_TRANSLATION_CONTRACT", "literary_contract"]

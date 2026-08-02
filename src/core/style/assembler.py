"""
Assemble a validated style-rule list into the prose blocks injected into the
translation and refinement prompts (Phase 3 of the style-extraction plan,
§2.5). Pure and deterministic — no I/O, no LLM call.
"""
from typing import Any, Dict, List, Optional

# Verbatim — do not paraphrase (plan §2.5).
_TRANSLATION_PREAMBLE_SOURCE = (
    "Match the following writing style in the translation. These rules describe how the "
    "text must read; they never authorize adding, removing, or altering content."
)

_TRANSLATION_PREAMBLE_MODEL = (
    "Imitate the following writing style, extracted from a reference work chosen as a "
    "stylistic model. Apply the rules to the translation while preserving the meaning of "
    "the source text exactly."
)

_REFINEMENT_PREAMBLE_SOURCE = (
    "Polish the already-translated text so that it matches the following writing style. "
    "Rewrite phrasing, rhythm and register as needed. Do not re-translate, do not add "
    "information, and do not change the meaning."
)

_REFINEMENT_PREAMBLE_MODEL = (
    "Polish the already-translated text so that it imitates the following writing style, "
    "extracted from a reference work chosen as a stylistic model. Rewrite phrasing, rhythm "
    "and register as needed. Do not re-translate, do not add information, and do not "
    "change the meaning."
)

# Appended verbatim to BOTH assembled blocks, after the rule list. Guards against the
# rules degenerating into a fixed vocabulary the model repeats chunk after chunk.
_ANTI_TIC_GUARD = (
    "Treat these rules as tendencies of the writing, not as a vocabulary. Never reuse a "
    "fixed set of words, phrases, or images across passages: vary the wording naturally "
    "and let each sentence follow from its own content. Whenever a rule and the natural "
    "phrasing of a passage conflict, favour the natural phrasing."
)

# Appended once, right after the "## Setting" section, whenever a preset carries a
# non-empty `context`. Keeps the model from reaching for a word that belongs to a
# later era or a higher technological level than the described setting.
_SETTING_GUARD = (
    "Do not use words that belong to a later era or a different technological level "
    "than this setting, even when they are the most direct equivalent."
)

_PREAMBLES = {
    "source": (_TRANSLATION_PREAMBLE_SOURCE, _REFINEMENT_PREAMBLE_SOURCE),
    "model": (_TRANSLATION_PREAMBLE_MODEL, _REFINEMENT_PREAMBLE_MODEL),
}


def assemble_instructions(
    mode: str, rules: List[Dict[str, Any]], context: str = ""
) -> Dict[str, Optional[str]]:
    """
    Turn `rules` (and an optional narrative-setting `context`) into the two
    prose blocks injected into the translation and refinement prompts.

    Body: one `f"- {instruction}"` line per rule, in order; a trailing "."
    is added only when the instruction ends with an alphanumeric character.
    `evidence` and `flags` (review-only metadata) never reach the output.

    When `context` is empty or blank, the output is byte-identical to the
    contextless form: `<preamble>\\n\\n<rule lines>\\n\\n<_ANTI_TIC_GUARD>`.
    When `context` is non-empty (and there is at least one rule), a
    "## Setting" section carrying `context.strip()` and `_SETTING_GUARD` is
    inserted between the preamble and a "## Style" section wrapping the
    rule lines.

    Returns {"translation": str | None, "refinement": str | None}. Both are
    None when no rule has a non-empty instruction — the anti-tic guard (and
    any setting section) is never emitted on its own, regardless of
    `context`. Raises ValueError when `mode` is not "source" or "model".
    """
    if mode not in _PREAMBLES:
        raise ValueError(f"unknown style mode: {mode!r}")

    translation_preamble, refinement_preamble = _PREAMBLES[mode]

    lines = []
    for rule in rules:
        instruction = str(rule.get("instruction", "")).strip()
        if not instruction:
            continue
        if instruction[-1].isalnum():
            instruction += "."
        lines.append(f"- {instruction}")

    if not lines:
        return {"translation": None, "refinement": None}

    body = "\n".join(lines)
    setting = context.strip()

    if not setting:
        translation = f"{translation_preamble}\n\n{body}\n\n{_ANTI_TIC_GUARD}"
        refinement = f"{refinement_preamble}\n\n{body}\n\n{_ANTI_TIC_GUARD}"
    else:
        setting_block = f"## Setting\n\n{setting}\n\n{_SETTING_GUARD}\n\n## Style\n\n{body}"
        translation = f"{translation_preamble}\n\n{setting_block}\n\n{_ANTI_TIC_GUARD}"
        refinement = f"{refinement_preamble}\n\n{setting_block}\n\n{_ANTI_TIC_GUARD}"

    return {"translation": translation, "refinement": refinement}

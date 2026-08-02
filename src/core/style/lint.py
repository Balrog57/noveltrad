"""
Conservative abstraction-violation lint for style-rule instructions (Phase 3
of the style-extraction plan). Detects quoted material, example markers,
enumerated word lists, proper nouns, and one-liners that are almost
certainly lexical rather than stylistic.

Pure and side-effect free. Detection is deliberately conservative: a false
positive costs the reviewer one click to dismiss a flag, while a false
negative bakes a language tic into every chunk of the translated book — so
the checks favour recall over precision, and the four assembled preambles
in `assembler.py` are written so that they lint clean themselves (see
`tests/unit/style/test_style_lint.py`).
"""
import re
from typing import Iterable, List, Optional, Set

from src.core.style.dimensions import ALLOWED_DIMENSIONS

TOO_SPECIFIC_MIN_CHARS = 25

_QUOTE_PATTERNS = (
    re.compile(r'"[^"]*[A-Za-z][^"]*"'),
    re.compile(r"'[^']*[A-Za-z][^']*'"),
    re.compile(r'«[^»]*[A-Za-z][^»]*»'),
    re.compile(r'“[^”]*[A-Za-z][^”]*”'),
    re.compile(r'‘[^’]*[A-Za-z][^’]*’'),
)

_EXAMPLE_MARKER_RE = re.compile(
    r'\b(e\.g\.|i\.e\.|for example|such as|for instance|'
    r'words like|expressions like|terms like|phrases like)\b',
    re.IGNORECASE,
)

_CLAUSE_SPLIT_RE = re.compile(r'[.;:!?]+')
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")

_COMMON_LANGUAGE_NAMES = {
    "english", "french", "spanish", "german", "italian", "portuguese",
    "chinese", "japanese", "korean", "russian", "dutch", "arabic",
    "polish", "turkish", "vietnamese", "swedish", "norwegian", "danish",
    "finnish", "greek", "hebrew", "hindi", "thai", "indonesian",
    "ukrainian", "czech", "romanian", "hungarian", "mandarin", "cantonese",
}


def _dimension_label_words() -> Set[str]:
    words: Set[str] = set()
    for dimension in ALLOWED_DIMENSIONS:
        words.update(dimension.split("_"))
    return words


_EXEMPT_WORDS = _COMMON_LANGUAGE_NAMES | _dimension_label_words()


def lint_instruction(text: str, *, extra_exempt: Optional[Iterable[str]] = None) -> List[str]:
    """
    Return the abstraction-violation codes detected in `text`, in this
    order: "quoted_example", "example_marker", "word_list", "proper_noun",
    "too_specific". Pure function — no I/O, no state.

    `extra_exempt` adds words (case-insensitive) to the proper-noun
    allowlist beyond the dimension labels and common language names — e.g.
    the source/target language names of the current request.
    """
    if not text:
        return []

    exempt = _EXEMPT_WORDS | {w.lower() for w in (extra_exempt or [])}

    flags: List[str] = []

    if any(pattern.search(text) for pattern in _QUOTE_PATTERNS):
        flags.append("quoted_example")

    if _EXAMPLE_MARKER_RE.search(text):
        flags.append("example_marker")

    if _has_word_list(text):
        flags.append("word_list")

    if _has_proper_noun(text, exempt):
        flags.append("proper_noun")

    if len(text.strip()) < TOO_SPECIFIC_MIN_CHARS:
        flags.append("too_specific")

    return flags


def _has_word_list(text: str) -> bool:
    """
    A comma/slash-separated run of 3+ items where every item in the run is
    1-2 tokens long. Clauses are split on sentence/clause punctuation first
    so that an introductory phrase before a colon (e.g. "Favor concrete
    nouns: rain, iron, dust, smoke.") doesn't count against the run, and a
    long trailing item correctly breaks it.
    """
    for clause in _CLAUSE_SPLIT_RE.split(text):
        items = [item.strip() for item in re.split(r'[,/]', clause) if item.strip()]
        if len(items) < 3:
            continue
        run = 0
        for item in items:
            token_count = len(_WORD_RE.findall(item))
            if 1 <= token_count <= 2:
                run += 1
                if run >= 3:
                    return True
            else:
                run = 0
    return False


def _has_proper_noun(text: str, exempt: Set[str]) -> bool:
    """
    Either a run of 2+ capitalized tokens not at sentence start (e.g.
    "Raymond Chandler"), or any single all-caps/CamelCase token. Sentence
    start is grammatical capitalization, not a proper-noun signal, so the
    first token of each sentence never starts (nor breaks into) a run —
    unless it is itself all-caps/CamelCase.
    """
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        tokens = _WORD_RE.findall(sentence)
        run = 0
        for index, token in enumerate(tokens):
            if token.lower() in exempt:
                run = 0
                continue
            is_all_caps = token.isupper() and len(token) >= 2
            is_camel_case = bool(re.search(r'[a-z][A-Z]', token))
            if is_all_caps or is_camel_case:
                return True
            is_sentence_start = index == 0
            if token[:1].isupper() and not is_sentence_start:
                run += 1
                if run >= 2:
                    return True
            else:
                run = 0
    return False

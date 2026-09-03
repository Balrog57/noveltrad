"""
Per-chunk glossary filtering.

Latin terms are matched with word boundaries (so "Fan" does not match "Fantasy").
CJK terms are matched as substrings (no word boundary concept in CJK scripts).
The filter returns only the subset of glossary entries that actually appear in
the chunk, sorted by source-term length (longest first) to handle overlaps.

When the per-chunk cap is hit, the kept subset is selected by occurrence count
(most frequent first, length as tiebreaker), then re-sorted by length for
output stability.

Source terms may declare alternative forms separated by '|' to handle inflected
languages (e.g. "Москва|Москве|Москвы|Москвой -> Moscou"). The filter matches
the entry if ANY of the alternatives appears in the chunk; occurrence counts
are summed across alternatives.
"""
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Tuple, Union

from src.core.glossary.models import GlossaryConfig

# Pre-compiled regex (Latin word-boundary terms) or lowercase needle (CJK/substring).
_MatchPattern = Union[re.Pattern, str]

_CJK_RE = re.compile(r'[぀-ゟ゠-ヿ一-鿿가-힯㐀-䶿]')


def _is_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def _has_word_char_at_edge(term: str) -> bool:
    """True if the term starts or ends with a regex \\w character (Latin/digit/underscore)."""
    if not term:
        return False
    return bool(re.match(r'\w', term[0])) or bool(re.match(r'\w', term[-1]))


def _split_alternatives(source: str) -> List[str]:
    """Split a source term on '|' into non-empty stripped alternatives."""
    if "|" not in source:
        stripped = source.strip()
        return [stripped] if stripped else []
    return [a.strip() for a in source.split("|") if a.strip()]


def _max_alt_length(source: str) -> int:
    """Length used for sort: the longest alternative wins (overlap handling)."""
    alts = _split_alternatives(source)
    return max((len(a) for a in alts), default=0)


@dataclass(frozen=True)
class _IndexedGlossaryEntry:
    source: str
    target: str
    patterns: Tuple[_MatchPattern, ...]
    # Lowercased (when case-insensitive) substring needles for O(C) prefilter
    # before regex/CJK counting — skips entries that cannot appear in the chunk.
    needles: Tuple[str, ...]


@lru_cache(maxsize=32)
def _build_glossary_index(
    terms_items: Tuple[Tuple[str, str], ...],
    case_sensitive: bool,
) -> Tuple[_IndexedGlossaryEntry, ...]:
    """Sort glossary terms and compile match patterns once per glossary.

    Called on every chunk but cached by (terms snapshot, case_sensitive).
    Avoids O(T log T) sort and O(T) regex compilation per chunk during
    translation — the dominant setup cost when T is large.
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    sorted_terms = sorted(
        terms_items,
        key=lambda kv: _max_alt_length(kv[0]),
        reverse=True,
    )
    entries: List[_IndexedGlossaryEntry] = []
    for source, target in sorted_terms:
        alternatives = _split_alternatives(source)
        if not alternatives:
            continue
        patterns: List[_MatchPattern] = []
        needles: List[str] = []
        for alt in alternatives:
            needle = alt if case_sensitive else alt.lower()
            needles.append(needle)
            if _is_cjk(alt) or not _has_word_char_at_edge(alt):
                patterns.append(needle)
            else:
                patterns.append(re.compile(r'\b' + re.escape(alt) + r'\b', flags))
        entries.append(_IndexedGlossaryEntry(source, target, tuple(patterns), tuple(needles)))
    return tuple(entries)


def _count_with_pattern(pattern: _MatchPattern, chunk: str, haystack: str) -> int:
    if isinstance(pattern, re.Pattern):
        return len(pattern.findall(chunk))
    return haystack.count(pattern)


def filter_glossary(
    chunk: str,
    glossary_terms: Dict[str, str],
    config: GlossaryConfig = None,
) -> Tuple[Dict[str, str], bool]:
    """
    Return only the glossary entries that appear in the chunk.

    Args:
        chunk: The source text to scan.
        glossary_terms: {source_term: translated_term}. A source_term may
            declare alternative inflected forms separated by '|'.
        config: GlossaryConfig (max_entries cap, case sensitivity).

    Returns:
        (filtered_terms, capped) where filtered_terms preserves order
        (longest source first) and capped is True if the cap was hit.
    """
    if not chunk or not glossary_terms:
        return {}, False

    config = config or GlossaryConfig()
    haystack = chunk if config.case_sensitive else chunk.lower()

    # Reuse pre-sorted, pre-compiled patterns for this glossary snapshot.
    index = _build_glossary_index(tuple(glossary_terms.items()), config.case_sensitive)

    matched: List[Tuple[str, str, int]] = []  # (source, target, occurrence_count)
    for entry in index:
        # Cheap O(C) substring check per alternative before regex/CJK counting.
        # Necessary for a match (word-boundary or substring); skips ~95% of entries
        # on large glossaries where only a few terms appear per chunk.
        if not any(needle in haystack for needle in entry.needles):
            continue
        total_count = sum(
            _count_with_pattern(pattern, chunk, haystack) for pattern in entry.patterns
        )
        if total_count > 0:
            matched.append((entry.source, entry.target, total_count))

    capped = False
    if config.max_entries and len(matched) > config.max_entries:
        capped = True
        # When capping, keep the most frequent terms first (length as
        # tiebreaker so longer-and-rarer beats shorter-and-rarer). This
        # is more useful than the previous length-only cut, which could
        # drop a high-frequency 2-char CJK name in favor of 50 longer
        # but rarer entries.
        kept = set(
            (s, t) for s, t, _ in
            sorted(matched, key=lambda x: (x[2], _max_alt_length(x[0])), reverse=True)[: config.max_entries]
        )
        # Preserve the original length-desc order in the output so the
        # rendered block stays predictable for the LLM.
        matched = [(s, t, c) for s, t, c in matched if (s, t) in kept]

    return {s: t for s, t, _ in matched}, capped

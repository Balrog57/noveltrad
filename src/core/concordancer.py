"""
Concordancier pour NovelTrad.
Moteur de recherche contextuel dans les mémoires de traduction et corpus du projet.
Conforme au cahier des charges §12.8.
"""
import re
from dataclasses import dataclass
from typing import Optional
from difflib import SequenceMatcher


@dataclass
class ConcordanceResult:
    """A single concordance search result."""
    source_text: str
    target_text: str
    score: float          # Relevance score 0.0-1.0
    match_type: str       # 'exact', 'fuzzy', 'substring'
    highlight_start: int  # Start position of match in source
    highlight_end: int    # End position of match in source
    origin: str           # 'tm' (translation memory), 'project' (current project segments)


class Concordancer:
    """
    Concordance search engine for NovelTrad.
    Searches across Translation Memory and project segments for contextual matches.

    Usage:
        concordancer = Concordancer()
        results = concordancer.search("cultivation", segments, tm_entries)
    """

    def __init__(self, fuzzy_threshold=0.6):
        """
        Args:
            fuzzy_threshold: Minimum similarity score for fuzzy matches (0.0-1.0).
        """
        self.fuzzy_threshold = fuzzy_threshold

    def search(self, query, segments=None, tm_entries=None,
               search_source=True, search_target=True, max_results=50):
        """
        Search for a term/expression across segments and TM.

        Args:
            query: Search term or expression.
            segments: List of segment objects with .source_text and .target_text
            tm_entries: List of TM entry objects with .source_text and .target_text
            search_source: Search in source text.
            search_target: Search in target text.
            max_results: Maximum number of results to return.

        Returns:
            list[ConcordanceResult]: Results sorted by relevance score.
        """
        if not query or not query.strip():
            return []

        query = query.strip()
        results = []

        # Search in project segments
        if segments:
            for seg in segments:
                self._search_in_pair(
                    query, seg.source_text, seg.target_text,
                    search_source, search_target,
                    origin='project', results=results
                )

        # Search in Translation Memory
        if tm_entries:
            for entry in tm_entries:
                src = entry.source_text if hasattr(entry, 'source_text') else entry[0]
                tgt = entry.target_text if hasattr(entry, 'target_text') else entry[1]
                self._search_in_pair(
                    query, src, tgt,
                    search_source, search_target,
                    origin='tm', results=results
                )

        # Sort by score descending, then deduplicate
        results.sort(key=lambda r: r.score, reverse=True)
        seen = set()
        unique_results = []
        for r in results:
            key = (r.source_text, r.target_text)
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        return unique_results[:max_results]

    def _search_in_pair(self, query, source_text, target_text,
                        search_source, search_target, origin, results):
        """Search for query in a single source/target pair."""
        query_lower = query.lower()

        # Exact/Substring match in source
        if search_source and source_text:
            source_lower = source_text.lower()
            pos = source_lower.find(query_lower)
            if pos != -1:
                results.append(ConcordanceResult(
                    source_text=source_text,
                    target_text=target_text or '',
                    score=1.0 if query_lower == source_lower else 0.9,
                    match_type='exact' if query_lower == source_lower else 'substring',
                    highlight_start=pos,
                    highlight_end=pos + len(query),
                    origin=origin,
                ))
                return  # Found exact/substring, skip fuzzy

        # Exact/Substring match in target
        if search_target and target_text:
            target_lower = target_text.lower()
            pos = target_lower.find(query_lower)
            if pos != -1:
                results.append(ConcordanceResult(
                    source_text=source_text or '',
                    target_text=target_text,
                    score=0.85,
                    match_type='substring',
                    highlight_start=pos,
                    highlight_end=pos + len(query),
                    origin=origin,
                ))
                return

        # Fuzzy match in source
        if search_source and source_text:
            similarity = SequenceMatcher(
                None, query_lower, source_text.lower()
            ).ratio()
            if similarity >= self.fuzzy_threshold:
                results.append(ConcordanceResult(
                    source_text=source_text,
                    target_text=target_text or '',
                    score=similarity * 0.8,  # Discount fuzzy a bit
                    match_type='fuzzy',
                    highlight_start=0,
                    highlight_end=0,
                    origin=origin,
                ))

    def search_regex(self, pattern, segments=None, tm_entries=None,
                     search_source=True, search_target=True, max_results=50):
        """
        Search using a regex pattern.

        Args:
            pattern: Regex pattern string.
            segments: Segments to search in.
            tm_entries: TM entries to search in.
            search_source: Search in source text.
            search_target: Search in target text.
            max_results: Max results.

        Returns:
            list[ConcordanceResult]: Matching results.
        """
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return []

        results = []
        all_pairs = []

        if segments:
            for seg in segments:
                all_pairs.append((seg.source_text, seg.target_text, 'project'))

        if tm_entries:
            for entry in tm_entries:
                src = entry.source_text if hasattr(entry, 'source_text') else entry[0]
                tgt = entry.target_text if hasattr(entry, 'target_text') else entry[1]
                all_pairs.append((src, tgt, 'tm'))

        for src, tgt, origin in all_pairs:
            if search_source and src:
                match = compiled.search(src)
                if match:
                    results.append(ConcordanceResult(
                        source_text=src,
                        target_text=tgt or '',
                        score=0.9,
                        match_type='exact',
                        highlight_start=match.start(),
                        highlight_end=match.end(),
                        origin=origin,
                    ))
                    continue

            if search_target and tgt:
                match = compiled.search(tgt)
                if match:
                    results.append(ConcordanceResult(
                        source_text=src or '',
                        target_text=tgt,
                        score=0.85,
                        match_type='exact',
                        highlight_start=match.start(),
                        highlight_end=match.end(),
                        origin=origin,
                    ))

            if len(results) >= max_results:
                break

        return results[:max_results]

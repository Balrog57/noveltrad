"""
Outil d'Alignement pour NovelTrad.
Aligne deux textes (source + traduction existante) pour créer des paires
de segments pouvant être exportées en TM/TMX.
Conforme au cahier des charges §13.3.
"""
import re
from dataclasses import dataclass
from typing import Optional
from src.core.segmenter import Segmenter


@dataclass
class AlignedPair:
    """A pair of aligned source and target segments."""
    source: str
    target: str
    confidence: float  # 0.0 to 1.0
    source_indices: list  # Original segment indices
    target_indices: list


class Aligner:
    """
    Aligns source and target texts to create translation pairs.

    Uses a combination of:
    - Length-based heuristics (Gale-Church inspired)
    - Anchor detection (numbers, proper nouns)
    - Sentence count balancing

    Usage:
        aligner = Aligner()
        pairs = aligner.align(source_text, target_text, src_lang='en', tgt_lang='fr')
    """

    def __init__(self):
        self.segmenter = Segmenter()

    def align(self, source_text, target_text, src_lang='en', tgt_lang='fr'):
        """
        Align source and target texts into pairs.

        Args:
            source_text: Full source text.
            target_text: Full target (translated) text.
            src_lang: Source language code.
            tgt_lang: Target language code.

        Returns:
            list[AlignedPair]: List of aligned sentence pairs.
        """
        if not source_text or not target_text:
            return []

        # Segment both texts
        source_segments = self.segmenter.segment(source_text, lang=src_lang)
        target_segments = self.segmenter.segment(target_text, lang=tgt_lang)

        if not source_segments or not target_segments:
            return []

        # Use dynamic programming alignment
        return self._dp_align(source_segments, target_segments)

    def align_segments(self, source_segments, target_segments):
        """
        Align pre-segmented source and target lists.

        Args:
            source_segments: List of source segments.
            target_segments: List of target segments.

        Returns:
            list[AlignedPair]: List of aligned pairs.
        """
        if not source_segments or not target_segments:
            return []
        return self._dp_align(source_segments, target_segments)

    def _dp_align(self, source_segs, target_segs):
        """
        Dynamic programming alignment using length-based cost
        (simplified Gale-Church algorithm).
        Supports 1:1, 1:2, 2:1, and 1:0/0:1 alignments.
        """
        m = len(source_segs)
        n = len(target_segs)

        # Cost matrix
        INF = float('inf')
        dp = [[INF] * (n + 1) for _ in range(m + 1)]
        dp[0][0] = 0.0
        back = [[None] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            for j in range(n + 1):
                if dp[i][j] == INF:
                    continue

                # 1:1 alignment
                if i < m and j < n:
                    cost = self._alignment_cost(
                        [source_segs[i]], [target_segs[j]]
                    )
                    if dp[i][j] + cost < dp[i + 1][j + 1]:
                        dp[i + 1][j + 1] = dp[i][j] + cost
                        back[i + 1][j + 1] = (i, j, '1:1')

                # 1:2 alignment (1 source → 2 target)
                if i < m and j + 1 < n:
                    cost = self._alignment_cost(
                        [source_segs[i]],
                        [target_segs[j], target_segs[j + 1]]
                    )
                    if dp[i][j] + cost < dp[i + 1][j + 2]:
                        dp[i + 1][j + 2] = dp[i][j] + cost
                        back[i + 1][j + 2] = (i, j, '1:2')

                # 2:1 alignment (2 source → 1 target)
                if i + 1 < m and j < n:
                    cost = self._alignment_cost(
                        [source_segs[i], source_segs[i + 1]],
                        [target_segs[j]]
                    )
                    if dp[i][j] + cost < dp[i + 2][j + 1]:
                        dp[i + 2][j + 1] = dp[i][j] + cost
                        back[i + 2][j + 1] = (i, j, '2:1')

                # 1:0 (skip source segment)
                if i < m:
                    skip_cost = len(source_segs[i]) * 0.5
                    if dp[i][j] + skip_cost < dp[i + 1][j]:
                        dp[i + 1][j] = dp[i][j] + skip_cost
                        back[i + 1][j] = (i, j, '1:0')

                # 0:1 (skip target segment)
                if j < n:
                    skip_cost = len(target_segs[j]) * 0.5
                    if dp[i][j] + skip_cost < dp[i][j + 1]:
                        dp[i][j + 1] = dp[i][j] + skip_cost
                        back[i][j + 1] = (i, j, '0:1')

        # Traceback
        pairs = []
        i, j = m, n
        while i > 0 or j > 0:
            if back[i][j] is None:
                break
            pi, pj, atype = back[i][j]

            if atype == '1:1':
                conf = self._confidence([source_segs[pi]], [target_segs[pj]])
                pairs.append(AlignedPair(
                    source=source_segs[pi],
                    target=target_segs[pj],
                    confidence=conf,
                    source_indices=[pi],
                    target_indices=[pj],
                ))
            elif atype == '1:2':
                merged_target = ' '.join([target_segs[pj], target_segs[pj + 1]])
                conf = self._confidence([source_segs[pi]], [target_segs[pj], target_segs[pj + 1]])
                pairs.append(AlignedPair(
                    source=source_segs[pi],
                    target=merged_target,
                    confidence=conf,
                    source_indices=[pi],
                    target_indices=[pj, pj + 1],
                ))
            elif atype == '2:1':
                merged_source = ' '.join([source_segs[pi], source_segs[pi + 1]])
                conf = self._confidence([source_segs[pi], source_segs[pi + 1]], [target_segs[pj]])
                pairs.append(AlignedPair(
                    source=merged_source,
                    target=target_segs[pj],
                    confidence=conf,
                    source_indices=[pi, pi + 1],
                    target_indices=[pj],
                ))
            # 1:0 and 0:1 are skipped (no pair produced)

            i, j = pi, pj

        pairs.reverse()
        return pairs

    def _alignment_cost(self, source_list, target_list):
        """
        Calculate alignment cost based on character length ratio.
        Good translations tend to preserve approximate length ratios.
        """
        src_len = sum(len(s) for s in source_list)
        tgt_len = sum(len(t) for t in target_list)

        if src_len == 0 and tgt_len == 0:
            return 0.0
        if src_len == 0 or tgt_len == 0:
            return max(src_len, tgt_len) * 0.5

        # Expected ratio: target is typically ~1.1x source for FR/EN
        ratio = tgt_len / src_len
        expected_ratio = 1.1
        deviation = abs(ratio - expected_ratio)

        # Anchor bonus: shared numbers reduce cost
        src_numbers = set(re.findall(r'\d+', ' '.join(source_list)))
        tgt_numbers = set(re.findall(r'\d+', ' '.join(target_list)))
        shared = len(src_numbers & tgt_numbers)
        anchor_bonus = shared * 0.5

        return deviation * 10 - anchor_bonus

    def _confidence(self, source_list, target_list):
        """Calculate confidence score for an alignment pair."""
        src_len = sum(len(s) for s in source_list)
        tgt_len = sum(len(t) for t in target_list)

        if src_len == 0 and tgt_len == 0:
            return 1.0
        if src_len == 0 or tgt_len == 0:
            return 0.1

        ratio = tgt_len / src_len
        deviation = abs(ratio - 1.1)

        # High confidence if length ratio is close to expected
        confidence = max(0.1, 1.0 - deviation * 0.5)
        return min(1.0, confidence)

    def export_pairs_as_tmx_data(self, pairs):
        """
        Convert aligned pairs to data suitable for TMX export.

        Args:
            pairs: list[AlignedPair]

        Returns:
            list[tuple]: List of (source_text, target_text) tuples.
        """
        return [(p.source, p.target) for p in pairs if p.source and p.target]

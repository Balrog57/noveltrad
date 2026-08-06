"""Segmentation (SDD 11.10, 11.14).

Budget: W = context_window_tokens; margin S = max(512, ceil(0.10 * W));
output reserve O = max(512, ceil(1.5 * T) + 64) <= max_output_tokens;
P = measured prompt/envelope cost. A call is allowed only when
P + T + O + S + C <= W. The target segment is reduced to a safe boundary;
neither prompt nor target segment is truncated.

C_min = 128 tokens per existing contextual source for pass 3, 0 otherwise.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from noveltrad.core.contracts import PipelineStage
from noveltrad.core.exceptions import ContextWindowError

_DIALOGUE_START = re.compile(r"^\s*(—|–|- |«|“)")


@dataclass(frozen=True, slots=True)
class Segment:
    offset_start: int
    offset_end: int
    text: str


def margin(window_tokens: int) -> int:
    return max(512, math.ceil(0.10 * window_tokens))


def output_reserve(segment_tokens: int, max_output_tokens: int) -> int:
    reserve = max(512, math.ceil(1.5 * segment_tokens) + 64)
    return min(reserve, max_output_tokens)


def count_tokens(text: str, mode: str = "utf8-bytes-v1") -> int:
    """Conservative token count: one token per UTF-8 byte (11.10)."""
    if mode == "utf8-bytes-v1":
        return len(text.encode("utf-8"))
    return len(text)


def context_budget(stage: PipelineStage, existing_sources: int, window_tokens: int) -> int:
    """Return C budget for the pass (128 tokens per existing source for
    pass 3, 0 for the other passes)."""
    if stage is PipelineStage.CONTEXT:
        return min(existing_sources * 128, max(0, window_tokens // 2))
    return 0


def can_fit(
    window_tokens: int,
    prompt_tokens: int,
    segment_tokens: int,
    max_output_tokens: int,
    context_tokens: int = 0,
) -> bool:
    total = (
        prompt_tokens
        + segment_tokens
        + output_reserve(segment_tokens, max_output_tokens)
        + margin(window_tokens)
        + context_tokens
    )
    return total <= window_tokens


def split_at_safe_boundaries(markdown: str) -> list[str]:
    """Split paragraphs at GFM-safe boundaries (11.14)."""
    paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip()]
    return paragraphs if paragraphs else [markdown]


def dialogue_block_start(paragraph: str) -> bool:
    return bool(_DIALOGUE_START.match(paragraph))


def segment_document(
    markdown: str,
    *,
    window_tokens: int,
    prompt_tokens: int,
    max_output_tokens: int,
    tokenizer_mode: str = "utf8-bytes-v1",
    stage: PipelineStage = PipelineStage.TRANSLATE,
) -> list[Segment]:
    """Return stable ordered segments; raise ContextWindowError when a
    single structural block cannot fit."""
    units = split_at_safe_boundaries(markdown)
    segments: list[Segment] = []
    current: list[str] = []
    current_offset = 0
    current_size = 0

    def flush(offset_start: int, parts: list[str]) -> None:
        nonlocal current_offset, current_size
        text = "\n\n".join(parts)
        segments.append(Segment(offset_start, offset_start + len(text), text))
        current_offset = offset_start + len(text) + 2
        current_size = 0

    offset = 0
    for unit in units:
        unit_size = count_tokens(unit, tokenizer_mode)
        fits_alone = can_fit(window_tokens, prompt_tokens, unit_size, max_output_tokens)
        if not fits_alone and (dialogue_block_start(unit) or not current):
            raise ContextWindowError(
                "SEGMENT_TOO_LARGE",
                "a single block exceeds the context window budget",
            )
        if current and not can_fit(
            window_tokens,
            prompt_tokens,
            current_size + 2 + unit_size,
            max_output_tokens,
        ):
            flush(current_offset, current)
            current = []
        if not current:
            current_offset = offset
        current.append(unit)
        current_size += (2 if len(current) > 1 else 0) + unit_size
        offset += len(unit) + 2
    if current:
        flush(current_offset, current)
    if not segments:
        raise ContextWindowError("SEGMENT_EMPTY", "no segment could be built")
    return segments

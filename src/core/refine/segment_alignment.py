"""Deterministic alignment of source and translated plain-text segments."""

from typing import Dict, List, Optional

from src.core.chunking.token_chunker import TokenChunker


def align_source_segments(
    source_text: str,
    target_chunks: List[Dict[str, str]],
    max_tokens_per_chunk: Optional[int] = None,
) -> List[str]:
    """Align source paragraphs with already-created target chunks.

    Translation preserves paragraph order but can change token counts. We first
    use the same chunker when the boundaries are identical, then fall back to
    paragraph-count and proportional boundaries. The returned list always has
    exactly one source string per target chunk.
    """
    if not target_chunks:
        return []
    if not source_text or not source_text.strip():
        return [""] * len(target_chunks)

    chunker = TokenChunker(max_tokens=max_tokens_per_chunk or 450)
    source_chunks = chunker.chunk_text(source_text)
    if len(source_chunks) == len(target_chunks):
        return [chunk.get("main_content", "") for chunk in source_chunks]

    source_paragraphs = chunker.split_into_paragraphs(source_text)
    target_counts = [
        max(1, len(chunker.split_into_paragraphs(chunk.get("main_content", ""))))
        for chunk in target_chunks
    ]
    if sum(target_counts) == len(source_paragraphs):
        aligned: List[str] = []
        cursor = 0
        for count in target_counts:
            aligned.append("\n\n".join(source_paragraphs[cursor:cursor + count]))
            cursor += count
        return aligned

    # A model may split or merge paragraphs. Keep ordering and cover the full
    # source using monotonic proportional boundaries instead of dropping it.
    aligned = []
    total_source = len(source_paragraphs)
    total_targets = len(target_chunks)
    for index in range(total_targets):
        start = round(index * total_source / total_targets)
        end = round((index + 1) * total_source / total_targets)
        if end <= start:
            end = min(total_source, start + 1)
        aligned.append("\n\n".join(source_paragraphs[start:end]))
    return aligned

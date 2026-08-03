"""
Plain-text translation pipeline used by Plain Text Mode.

Skips placeholder preservation and HTML chunking entirely. Paragraphs are
grouped into token-budgeted segments that remember which source paragraph
indices they cover, translated with has_placeholders=False, then written back
to those exact indices. Empty source paragraphs (image-only blocks) are never
sent to the LLM and keep their slot; a paragraph larger than the token budget
is split into sentence pieces that all collapse back into its single slot
(issue #203: count-only realignment shifted every paragraph after an empty or
oversized block).

Used by the EPUB and DOCX adapters when prompt_options['plain_text_mode'] is True.
"""
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.chunking.token_chunker import TokenChunker
from src.core.translator import generate_translation_request
from src.core.post_processor import clean_translated_text
from src.core.epub.translation_metrics import TranslationMetrics
from src.core.common.parallel import aclosing, iter_ordered_concurrent
from src.core.llm.exceptions import RateLimitError


PARAGRAPH_SEPARATOR = "\n\n"
_RESPLIT_REGEX = re.compile(r"\n{2,}")
_MARKUP_TAG_REGEX = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*?)?/?>")


def strip_hallucinated_markup(translated: str, source: str) -> str:
    """Remove HTML-like tags the model invented in Plain Text Mode.

    Plain Text Mode never sends markup to the LLM, so a tag in the output is
    model noise (e.g. small models wrap ordinals or footnote numbers in
    <sup>...</sup>). Only the tags are dropped; their inner text is kept.
    Chunks whose source legitimately contains '<' (code samples inside <pre>
    blocks) are left untouched to avoid damaging real content.
    """
    if "<" not in translated or "<" in source:
        return translated
    return _MARKUP_TAG_REGEX.sub("", translated)


def _split_translated_back_to_paragraphs(translated_text: str) -> List[str]:
    """Split a translated blob into paragraphs (tolerates 2+ newlines)."""
    return [p.strip() for p in _RESPLIT_REGEX.split(translated_text) if p.strip()]


def _reconcile_paragraph_counts(
    translated_paragraphs: List[str],
    expected_count: int,
) -> List[str]:
    """
    Best-effort alignment when the LLM merged or split paragraphs inside one
    segment. The blast radius is the segment, never the whole document.

    - translated == expected: return as-is
    - translated < expected: pad with empty strings
    - translated > expected: merge surplus into the last slot
    """
    got = len(translated_paragraphs)
    if got == expected_count:
        return translated_paragraphs
    if got < expected_count:
        return translated_paragraphs + [""] * (expected_count - got)
    head = translated_paragraphs[:expected_count - 1]
    tail = " ".join(translated_paragraphs[expected_count - 1:])
    return head + [tail]


def build_plain_segments(
    paragraphs: List[str],
    max_tokens_per_chunk: int,
) -> List[Dict[str, Any]]:
    """
    Group source paragraphs into translation segments that track their indices.

    Each segment is {'indices': [int, ...], 'text': str, 'partial': bool}:
    - whole-paragraph segments cover consecutive non-empty paragraphs joined
      with PARAGRAPH_SEPARATOR ('partial' False, one index per paragraph);
    - an oversized paragraph yields several sentence-piece segments that share
      the same single index ('partial' True).

    Empty/whitespace-only paragraphs are skipped here and restored by index at
    reassembly time.
    """
    chunker = TokenChunker(max_tokens=max_tokens_per_chunk)
    sep_tokens = chunker.count_tokens(PARAGRAPH_SEPARATOR)

    segments: List[Dict[str, Any]] = []
    cur_indices: List[int] = []
    cur_texts: List[str] = []
    cur_tokens = 0

    def flush():
        nonlocal cur_indices, cur_texts, cur_tokens
        if cur_indices:
            segments.append({
                'indices': cur_indices,
                'text': PARAGRAPH_SEPARATOR.join(cur_texts),
                'partial': False,
            })
            cur_indices, cur_texts, cur_tokens = [], [], 0

    for idx, paragraph in enumerate(paragraphs):
        text = paragraph or ""
        if not text.strip():
            continue

        tokens = chunker.count_tokens(text)

        if tokens > chunker.max_tokens:
            flush()
            sentences = chunker.split_paragraph_into_sentences(text)
            if len(sentences) > 1:
                # _chunk_units returns {"text", "join_before"} records; this
                # pipeline tracks paragraph identity itself and only needs the text.
                pieces = [p["text"] for p in chunker._chunk_units(sentences, separator=" ")]
            else:
                pieces = [text]
            for piece in pieces:
                segments.append({'indices': [idx], 'text': piece, 'partial': True})
            continue

        potential = cur_tokens + tokens + (sep_tokens if cur_indices else 0)
        if cur_indices and potential > chunker.max_tokens:
            flush()
        cur_indices.append(idx)
        cur_texts.append(text)
        cur_tokens = cur_tokens + tokens + (sep_tokens if len(cur_indices) > 1 else 0)

    flush()
    return segments


def _reassemble(
    segments: List[Dict[str, Any]],
    translated_parts: List[str],
    source_paragraphs: List[str],
) -> List[str]:
    """
    Write each segment's translation back to the source indices it covers.

    Empty source slots keep their original (empty) value; pieces of an
    oversized paragraph are concatenated in order into its single slot.
    """
    out: List[Optional[str]] = [None] * len(source_paragraphs)
    partial_pieces: Dict[int, List[str]] = {}

    for segment, translated in zip(segments, translated_parts):
        text = translated or ""
        if segment['partial']:
            partial_pieces.setdefault(segment['indices'][0], []).append(text.strip())
        else:
            parts = _split_translated_back_to_paragraphs(text)
            parts = _reconcile_paragraph_counts(parts, len(segment['indices']))
            for k, idx in enumerate(segment['indices']):
                out[idx] = parts[k]

    for idx, pieces in partial_pieces.items():
        out[idx] = " ".join(p for p in pieces if p)

    return [
        slot if slot is not None else source_paragraphs[i]
        for i, slot in enumerate(out)
    ]


async def translate_paragraphs_plain(
    paragraphs: List[str],
    source_language: str,
    target_language: str,
    model_name: str,
    llm_client: Any,
    max_tokens_per_chunk: int,
    log_callback: Optional[Callable] = None,
    stats_callback: Optional[Callable] = None,
    context_manager: Optional[Any] = None,
    check_interruption_callback: Optional[Callable] = None,
    prompt_options: Optional[Dict] = None,
    parallel_workers: int = 1,
    *,
    resume_segments: Optional[List[Dict[str, Any]]] = None,
    resume_translated: Optional[List[str]] = None,
    checkpoint_hook: Optional[Callable[[List[Dict[str, Any]], List[str], int, Dict[str, Any]], None]] = None,
    checkpoint_every: int = 5,
) -> Tuple[List[str], TranslationMetrics, bool]:
    """
    Translate a list of plain-text paragraphs without placeholder preservation.

    Args:
        paragraphs: source paragraphs (one string per block)
        source_language, target_language: language names
        model_name, llm_client: LLM config
        max_tokens_per_chunk: chunking budget
        log_callback, stats_callback: callbacks (stats_callback receives
            file-local stats via TranslationMetrics.to_dict(); callers that
            aggregate across files are responsible for adding their global
            offset to completed_chunks).
        context_manager: AdaptiveContextManager (Ollama)
        check_interruption_callback: returns True to abort
        prompt_options: prompt customization (text_cleanup, glossary, etc.)
        parallel_workers: number of chunks translated concurrently (already
            resolved against the provider by the caller). When 1, behavior is
            identical to the legacy sequential loop, including previous-chunk
            context chaining; > 1 drops that chaining.
        resume_segments: segment list from a previous run's checkpoint, replayed
            verbatim instead of re-deriving it from `paragraphs`. Storing the
            segmentation rather than rebuilding it makes resume immune to a
            token-budget change between the pause and the resume.
        resume_translated: translations already produced for the first
            len(resume_translated) segments. Those segments are never retried,
            including ones that fell back to source text after a failure.
        checkpoint_hook: called as
            hook(segments, prefix, next_index, stats_dict) whenever the
            contiguous translated prefix advances far enough to be worth
            persisting. `prefix` is always exactly `next_index` items long and
            contains no None. A hook that raises is logged and ignored.
        checkpoint_every: how many segments between periodic hook calls.

    Returns:
        (translated_paragraphs, stats, was_interrupted)
    """
    stats = TranslationMetrics()

    source = list(paragraphs)
    if not source or all(not (p or "").strip() for p in source):
        if stats_callback:
            stats_callback(stats.to_dict())
        return source, stats, False

    # === RESUME ===
    # build_plain_segments is deterministic for a given (paragraphs, budget),
    # but the stored segmentation always wins so a budget change between pause
    # and resume cannot shift the indices the prefix was written against.
    prefix: List[str] = list(resume_translated or [])
    segments = (
        list(resume_segments) if resume_segments is not None
        else build_plain_segments(source, max_tokens_per_chunk)
    )
    if prefix and (resume_segments is None or len(prefix) > len(segments)):
        # More translated segments than segments to translate means the source
        # changed under the checkpoint; nothing about the prefix can be trusted.
        if log_callback:
            log_callback(
                "plain_text_resume_discarded",
                "⚠️ Plain-text checkpoint does not match the source, restarting this file"
            )
        prefix = []
        segments = build_plain_segments(source, max_tokens_per_chunk)

    # Chunk dicts mirror split_text_into_chunks() output; context comes from
    # the neighboring segments.
    chunks: List[Dict[str, str]] = []
    for i, segment in enumerate(segments):
        if i > 0:
            context_before = segments[i - 1]['text'].split(PARAGRAPH_SEPARATOR)[-1]
        else:
            context_before = ""
        if i < len(segments) - 1:
            context_after = segments[i + 1]['text'].split(PARAGRAPH_SEPARATOR)[0]
        else:
            context_after = ""
        chunks.append({
            'context_before': context_before,
            'main_content': segment['text'],
            'context_after': context_after,
        })

    stats.total_chunks = len(chunks)

    workers = max(1, int(parallel_workers))
    sequential = workers == 1

    # Index-addressed results so out-of-order completion still reassembles in
    # source order.
    translated_parts: List[Optional[str]] = [None] * len(chunks)
    previous_translation_context = ""

    # Restored work counts as processed so the progress bar does not rewind.
    for k, done in enumerate(prefix):
        translated_parts[k] = done
        stats.record_processed()

    if stats_callback:
        stats_callback(stats.to_dict())

    async def _translate_chunk(i):
        """Translate one chunk. Reads previous_translation_context only in
        sequential mode (parallel runs have no stable previous chunk)."""
        main_content = chunks[i].get('main_content', '')
        if not main_content.strip():
            return ('empty', main_content)
        translated = await generate_translation_request(
            main_content=main_content,
            context_before=chunks[i].get('context_before', ''),
            context_after=chunks[i].get('context_after', ''),
            previous_translation_context=(previous_translation_context if sequential else ""),
            source_language=source_language,
            target_language=target_language,
            model=model_name,
            llm_client=llm_client,
            log_callback=log_callback,
            has_placeholders=False,
            prompt_options=prompt_options,
            context_manager=context_manager,
            placeholder_format=None,
        )
        return ('done', translated)

    def _fill_remaining_with_source():
        for j in range(len(chunks)):
            if translated_parts[j] is None:
                translated_parts[j] = chunks[j].get('main_content', '')

    def _run_checkpoint_hook(next_index):
        """Hand the contiguous prefix [0, next_index) to the caller's hook.

        A failing hook degrades persistence, not the translation, so every call
        is isolated.
        """
        if checkpoint_hook is None:
            return
        try:
            checkpoint_hook(
                segments, list(translated_parts[:next_index]), next_index, stats.to_dict()
            )
        except Exception as exc:  # noqa: BLE001 - checkpointing is best-effort
            if log_callback:
                log_callback(
                    "plain_text_checkpoint_failed",
                    f"⚠️ Plain-text checkpoint failed at segment {next_index}/{len(chunks)}: {exc}"
                )

    checkpoint_step = max(1, int(checkpoint_every))
    pending = list(range(len(prefix), len(chunks)))
    rate_limit_error = None
    processed = len(prefix)

    # Continuous concurrency with in-order delivery (see iter_ordered_concurrent).
    # aclosing() is required: the rate-limit branch breaks out of the loop, and
    # only closing the generator cancels the requests still in flight.
    async with aclosing(iter_ordered_concurrent(
        pending, workers, _translate_chunk, check_interruption_callback
    )) as stream:
        async for i, result in stream:
            main_content = chunks[i].get('main_content', '')

            if isinstance(result, RateLimitError):
                rate_limit_error = result
                break

            if isinstance(result, Exception):
                if log_callback:
                    log_callback(
                        "plain_text_chunk_failed",
                        f"Chunk {i + 1}/{len(chunks)} failed ({result}) - keeping original text"
                    )
                translated_parts[i] = main_content
                stats.failed_chunks += 1
            else:
                kind, value = result
                if kind == 'empty':
                    translated_parts[i] = value
                    stats.successful_first_try += 1
                elif value is None:
                    if log_callback:
                        log_callback(
                            "plain_text_chunk_failed",
                            f"Chunk {i + 1}/{len(chunks)} failed - keeping original text"
                        )
                    translated_parts[i] = main_content
                    stats.failed_chunks += 1
                else:
                    cleaned = clean_translated_text(value)
                    cleaned = strip_hallucinated_markup(
                        cleaned, chunks[i].get('main_content', ''))
                    translated_parts[i] = cleaned
                    stats.successful_first_try += 1
                    if sequential:
                        words = cleaned.split()
                        previous_translation_context = (
                            " ".join(words[-25:]) if len(words) > 25 else cleaned
                        )

            stats.record_processed()
            if stats_callback:
                stats_callback(stats.to_dict())
            processed += 1

            # === CONTIGUITY INVARIANT ===
            # iter_ordered_concurrent yields indices strictly in ascending order
            # and every branch above assigns translated_parts[i] (success, empty,
            # None result, or exception -> source fallback). Therefore, once index
            # i has been handled, slots 0..i are all non-None and i + 1 is a
            # gap-free resume point. Every hook call below relies on this: the
            # prefix handed to the checkpoint is never sparse.
            next_index = i + 1
            if next_index % checkpoint_step == 0 or next_index == len(chunks):
                _run_checkpoint_hook(next_index)

    if rate_limit_error is not None:
        # Persist the contiguous prefix translated before the limit, then keep
        # source text for everything else and propagate: the caller's auto-pause
        # depends on the exception reaching it.
        _run_checkpoint_hook(processed)
        _fill_remaining_with_source()
        safe_parts = [p if p is not None else "" for p in translated_parts]
        rate_limit_error.partial_result = _reassemble(segments, safe_parts, source)
        raise rate_limit_error

    # Interruption: the scheduler stopped launching new chunks; keep source text
    # for the uncommitted tail and report the interruption.
    if processed < len(chunks) and check_interruption_callback and check_interruption_callback():
        if log_callback:
            log_callback(
                "plain_text_translation_interrupted",
                f"⏸️ Plain-text translation interrupted at chunk {processed + 1}/{len(chunks)}"
            )
        _run_checkpoint_hook(processed)
        _fill_remaining_with_source()
        safe_parts = [p if p is not None else "" for p in translated_parts]
        return _reassemble(segments, safe_parts, source), stats, True

    # Any None left (shouldn't happen) falls back to empty string.
    safe_parts = [p if p is not None else "" for p in translated_parts]
    return _reassemble(segments, safe_parts, source), stats, False

"""
Translation module for LLM communication
"""
import asyncio
import time
import re
from tqdm.auto import tqdm

from src.config import (
    DEFAULT_MODEL, TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT, SENTENCE_TERMINATORS,
    THINKING_MODELS, ADAPTIVE_CONTEXT_INITIAL_THINKING, MAX_TRANSLATION_ATTEMPTS
)
from src.prompts.prompts import generate_translation_prompt, generate_subtitle_block_prompt, generate_refinement_prompt
from src.prompts.examples import ensure_example_ready, has_example_for_pair, PLACEHOLDER_EXAMPLES
from .llm_client import default_client, LLMClient, create_llm_client, LLMResponse
from .llm import (
    ContextOverflowError,
    RepetitionLoopError,
    RateLimitError,
    RefinementInterrupted,
)
from .post_processor import clean_translated_text
from .context_optimizer import (
    AdaptiveContextManager,
    validate_configuration,
    INITIAL_CONTEXT_SIZE,
    CONTEXT_STEP
)
from .progress_tracker import TokenProgressTracker
from .chunking.token_chunker import TokenChunker
from .llm.utils.extraction import TranslationExtractor
from typing import List, Dict, Tuple, Optional

# Shared inspector so one-pass EPUB and refine agree on unclosed-tag salvage.
_TAG_INSPECTOR = TranslationExtractor(TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT)


# Configuration for context overflow recovery
MAX_CHUNK_REDUCTION_ATTEMPTS = 3
CHUNK_REDUCTION_FACTOR = 0.6  # Reduce to 60% of original size each attempt
MIN_CHUNK_CHARACTERS = 200  # Minimum chunk size to attempt translation


def _build_chunk_glossary_block(
    chunk_content: str,
    prompt_options: Optional[dict],
    log_callback=None,
    runtime_state: Optional[dict] = None,
    *,
    target_language: str = "",
) -> str:
    """
    Filter the active glossary against the current chunk and render a prompt block.

    Reads `glossary_terms` (dict source -> target) and optional `glossary_config`
    (GlossaryConfig) from prompt_options. Returns "" when no glossary is active
    or when the glossary has neither a term matching this chunk nor any gendered
    entity.

    Two sections may be emitted:
      - the cast block (gendered entities). Names in this chunk are kept
        first when the list is capped; remaining slots stay in glossary
        order so pronoun-only references still have a core cast;
      - the glossary block, restricted to terms present in this chunk.

    When the per-chunk cap is hit and `warn_on_cap` is enabled, logs a single
    warning per job. The dedupe flag lives in `runtime_state` (a transient dict
    owned by the caller) so it never leaks into the persisted prompt_options
    snapshot. If runtime_state is None, a fresh local dict is used (warning
    won't be deduped across calls — fine for ad-hoc uses).

    Keyword-only args:
        target_language: the job's target language, forwarded to
            `build_glossary_block`. It selects the target-side inflection
            instruction, emitted only for the languages listed in
            `INFLECTED_TARGET_LANGUAGES` (see src/core/glossary/inflection.py).
            Defaults to "" so existing callers keep the previous output.
    """
    if not prompt_options:
        return ""
    terms = prompt_options.get("glossary_terms")
    if not terms:
        return ""
    try:
        from src.core.glossary import (
            build_cast_block,
            build_glossary_block,
            filter_glossary,
            GlossaryConfig,
        )
    except ImportError:
        return ""
    config = prompt_options.get("glossary_config") or GlossaryConfig()
    filtered, capped = filter_glossary(chunk_content, terms, config)

    if runtime_state is None:
        runtime_state = {}

    if capped and config.warn_on_cap and "glossary_cap_warned" not in runtime_state:
        runtime_state["glossary_cap_warned"] = True
        if log_callback:
            log_callback(
                "glossary_capped",
                f"⚠️ Glossary cap reached: more than {config.max_entries} terms matched in a single chunk. "
                f"Excess entries are dropped — increase `max_entries` if you need full coverage."
            )

    metadata = prompt_options.get("glossary_term_metadata") or None

    cast_block, cast_capped = build_cast_block(
        terms,
        term_metadata=metadata,
        max_entries=getattr(config, "max_cast_entries", None) or 0,
        chunk_content=chunk_content,
        matched_sources=set(filtered),
    )

    if (
        cast_capped
        and config.warn_on_cap
        and "cast_cap_warned" not in runtime_state
    ):
        runtime_state["cast_cap_warned"] = True
        if log_callback:
            log_callback(
                "glossary_cast_capped",
                f"⚠️ Cast list capped at {config.max_cast_entries} gendered names "
                f"(the glossary has more). Names in the current chunk are kept "
                f"first; raise `max_cast_entries` to list the whole cast every chunk."
            )

    glossary_block = (
        build_glossary_block(
            filtered, target_language=target_language, term_metadata=metadata
        ) if filtered else ""
    )

    if not cast_block and not glossary_block:
        return ""
    if not cast_block:
        return glossary_block
    if not glossary_block:
        return cast_block
    return f"{cast_block}\n{glossary_block}"


def _build_refinement_glossary_block(
    source_text: str,
    draft_text: str,
    prompt_options: Optional[dict],
    log_callback=None,
    runtime_state: Optional[dict] = None,
    *,
    target_language: str = "",
) -> str:
    """Filter glossary against source text, falling back to source+draft."""
    lookup = "\n".join(
        part for part in (source_text or "", draft_text or "") if part.strip()
    )
    return _build_chunk_glossary_block(
        lookup,
        prompt_options,
        log_callback=log_callback,
        runtime_state=runtime_state,
        target_language=target_language,
    )


def split_chunk_for_retry(main_content: str, target_ratio: float = 0.5) -> Tuple[str, str]:
    """
    Split a chunk into two parts for retry after context overflow.

    Tries to split at a sentence boundary near the target ratio.

    Args:
        main_content: The text content to split
        target_ratio: Target position for split (0.5 = middle)

    Returns:
        Tuple of (first_half, second_half)
    """
    if not main_content.strip():
        return main_content, ""

    lines = main_content.split('\n')
    if len(lines) <= 1:
        # For single line, split at sentence boundary or middle
        target_pos = int(len(main_content) * target_ratio)

        # Look for sentence terminators near target position
        best_split = target_pos
        for terminator in SENTENCE_TERMINATORS:
            # Search in a window around target position
            search_start = max(0, target_pos - 100)
            search_end = min(len(main_content), target_pos + 100)
            search_area = main_content[search_start:search_end]

            term_pos = search_area.rfind(terminator)
            if term_pos != -1:
                actual_pos = search_start + term_pos + len(terminator)
                if abs(actual_pos - target_pos) < abs(best_split - target_pos):
                    best_split = actual_pos

        return main_content[:best_split].strip(), main_content[best_split:].strip()

    # For multi-line content, split at line boundaries
    target_line = int(len(lines) * target_ratio)

    # Look for a sentence-ending line near target
    best_line = target_line
    for i in range(max(0, target_line - 5), min(len(lines), target_line + 5)):
        line_stripped = lines[i].strip()
        if line_stripped and line_stripped.endswith(SENTENCE_TERMINATORS):
            best_line = i + 1
            break

    first_half = '\n'.join(lines[:best_line])
    second_half = '\n'.join(lines[best_line:])

    return first_half.strip(), second_half.strip()





async def _make_llm_request_with_adaptive_context(
    main_content: str,
    context_before: str,
    context_after: str,
    previous_translation_context: str,
    source_language: str,
    target_language: str,
    model: str,
    llm_client,
    log_callback,
    has_placeholders: bool,
    prompt_options: dict = None,
    context_manager: AdaptiveContextManager = None,
    placeholder_format: Optional[Tuple[str, str]] = None,
    runtime_state: Optional[dict] = None,
) -> Tuple[Optional[str], str, Optional[LLMResponse]]:
    """
    Make LLM request with adaptive context sizing.

    This function uses the AdaptiveContextManager to:
    1. Start with a small context
    2. Retry with larger context if needed
    3. Return token usage info for the manager to learn from

    Args:
        main_content: Text to translate
        context_before: Context before main content
        context_after: Context after main content
        previous_translation_context: Previous translation for consistency
        source_language: Source language
        target_language: Target language
        model: LLM model name
        llm_client: LLM client instance
        log_callback: Logging callback function
        has_placeholders: If True, includes placeholder preservation instructions (for EPUB HTML tags)
        prompt_options: Optional dict with prompt customization options
        context_manager: AdaptiveContextManager for context sizing

    Returns:
        Tuple of (translated_text or None, actual_content_translated, LLMResponse)
    """
    current_content = main_content
    remaining_content = ""
    all_translations = []
    reduction_attempt = 0
    empty_retries = 0
    last_response: Optional[LLMResponse] = None

    while current_content.strip():
        try:
            # Build the per-chunk glossary block (empty if no glossary configured)
            glossary_block = _build_chunk_glossary_block(
                current_content, prompt_options, log_callback=log_callback,
                runtime_state=runtime_state, target_language=target_language,
            )

            # Generate prompts
            prompt_pair = generate_translation_prompt(
                current_content,
                context_before,
                context_after,
                previous_translation_context,
                source_language,
                target_language,
                has_placeholders=has_placeholders,
                prompt_options=prompt_options,
                placeholder_format=placeholder_format,
                glossary_block=glossary_block,
            )

            # Log the request
            if log_callback and reduction_attempt == 0:
                log_callback("llm_request", "Sending request to LLM", data={
                    'type': 'llm_request',
                    'system_prompt': prompt_pair.system,
                    'user_prompt': prompt_pair.user,
                    'model': model
                })

            start_time = time.time()
            client = llm_client or default_client

            # Set context from manager if available
            if context_manager and hasattr(client, 'context_window'):
                new_ctx = context_manager.get_context_size()
                if client.context_window != new_ctx:
                    if log_callback:
                        log_callback("context_update",
                            f"📐 Updating context window: {client.context_window} → {new_ctx}")
                    else:
                        tqdm.write(f"\n📐 Context: {client.context_window} → {new_ctx}")
                client.context_window = new_ctx

            llm_response = await client.generate(
                prompt_pair.user, system_prompt=prompt_pair.system
            )
            execution_time = time.time() - start_time

            if not llm_response:
                return None, main_content, None

            last_response = llm_response
            full_raw_response = llm_response.content or ""

            if not str(full_raw_response).strip():
                # Empty/null content. Aggregators (OpenRouter, OpenCode, …) drop
                # completions with 0 tokens; that is usually transient, not a
                # policy refusal. Retry with backoff before failing the chunk.
                empty_retries += 1
                tokens = llm_response.completion_tokens or 0
                if empty_retries < MAX_TRANSLATION_ATTEMPTS:
                    delay = min(8, 2 * empty_retries)
                    if log_callback:
                        log_callback("empty_llm_retry",
                            f"⚠️ Empty response ({tokens} completion tokens) — "
                            f"retrying in {delay}s "
                            f"({empty_retries}/{MAX_TRANSLATION_ATTEMPTS}). "
                            f"Often a dropped completion from the provider, not a refusal.")
                    await asyncio.sleep(delay)
                    continue
                if log_callback:
                    log_callback("empty_llm_response",
                        f"⚠️ Model returned an empty response after "
                        f"{empty_retries} attempts ({tokens} completion tokens). "
                        f"This can be a flaky aggregator, a dropped completion, "
                        f"or a content filter. The chunk will be retried by the "
                        f"pipeline; if it keeps failing, try another model.")
                return None, main_content, last_response

            # Check if we should retry with larger context (adaptive strategy)
            if context_manager and llm_response.was_truncated:
                if context_manager.should_retry_with_larger_context(
                    llm_response.was_truncated, llm_response.context_used
                ):
                    context_manager.increase_context()
                    continue  # Retry with larger context

            # Log the response
            if log_callback:
                log_callback("llm_response", "LLM Response received", data={
                    'type': 'llm_response',
                    'response': full_raw_response,
                    'execution_time': execution_time,
                    'model': model,
                    'tokens': {
                        'prompt': llm_response.prompt_tokens,
                        'completion': llm_response.completion_tokens,
                        'total': llm_response.context_used,
                        'limit': llm_response.context_limit
                    }
                })

            # Extract translation. An omitted </TRANSLATION> is salvaged so
            # one-pass EPUB keeps the body the same way refine already did.
            translated_text = client.extract_translation(full_raw_response)
            unclosed = _TAG_INSPECTOR.omitted_closing_tag(full_raw_response)

            if translated_text and unclosed and llm_response.was_truncated:
                # Salvaged a cut-off completion. Prefer a smaller slice over a
                # mid-sentence chunk. Growing num_ctx does nothing on cloud
                # routers (OpenRouter, OpenCode, …): the limit is max_tokens.
                if reduction_attempt < MAX_CHUNK_REDUCTION_ATTEMPTS:
                    reduction_attempt += 1
                    reduction_factor = CHUNK_REDUCTION_FACTOR ** reduction_attempt
                    first_part, second_part = split_chunk_for_retry(
                        current_content, reduction_factor
                    )
                    if len(first_part) >= MIN_CHUNK_CHARACTERS:
                        if log_callback:
                            log_callback(
                                "truncated_translation_split",
                                "⚠️ Output truncated before </TRANSLATION>. "
                                f"Splitting the chunk ({reduction_factor * 100:.0f}%) "
                                f"and retrying "
                                f"({reduction_attempt}/{MAX_CHUNK_REDUCTION_ATTEMPTS})...",
                            )
                        current_content = first_part
                        if second_part.strip():
                            remaining_content = second_part + (
                                "\n" + remaining_content if remaining_content else ""
                            )
                        continue
                if context_manager and context_manager.should_retry_with_larger_context(
                    True, llm_response.context_used
                ):
                    if log_callback:
                        log_callback(
                            "implicit_truncation_retry",
                            "🔄 Output truncated before closing tag. "
                            "Retrying with larger context...",
                        )
                    context_manager.increase_context()
                    continue
                if log_callback:
                    log_callback(
                        "translation_unclosed_tag_salvaged",
                        "⚠️ Output truncated; using the partial translation "
                        "(could not split further).",
                    )

            if translated_text:
                if unclosed and not llm_response.was_truncated and log_callback:
                    log_callback(
                        "translation_unclosed_tag_salvaged",
                        "⚠️ Model omitted </TRANSLATION> — using the translated text anyway.",
                    )
                all_translations.append(translated_text)
                empty_retries = 0
            else:
                # Extraction failed - tags not found or malformed
                if log_callback:
                    log_callback("translation_extraction_failed",
                        "⚠️ WARNING: Failed to extract translation (tags not found or malformed)")
                    log_callback("translation_extraction_failed_preview",
                        f"Response preview (first 300 chars): {full_raw_response[:300]}")

                # Only grow context when the provider actually hit an output
                # limit. A missing closer with finish_reason=stop is not a
                # context-window problem (and OpenRouter/OpenCode ignore num_ctx anyway).
                if llm_response.was_truncated:
                    if context_manager and context_manager.should_retry_with_larger_context(
                        True, llm_response.context_used
                    ):
                        if log_callback:
                            log_callback("implicit_truncation_retry",
                                "🔄 Model stopped before closing tag. Retrying with larger context...")
                        context_manager.increase_context()
                        continue  # Retry with larger context

                empty_retries += 1
                if empty_retries < MAX_TRANSLATION_ATTEMPTS:
                    delay = min(8, 2 * empty_retries)
                    if log_callback:
                        log_callback(
                            "translation_extraction_retry",
                            f"⚠️ Malformed translation tags — retrying in {delay}s "
                            f"({empty_retries}/{MAX_TRANSLATION_ATTEMPTS}).",
                        )
                    await asyncio.sleep(delay)
                    continue

                # For EPUB with placeholders, failing to extract is CRITICAL
                # because using the raw response would include <TRANSLATION> tags in the HTML
                if has_placeholders:
                    if log_callback:
                        log_callback("epub_extraction_critical_fail",
                            "CRITICAL: Cannot use raw response for EPUB (would corrupt HTML structure)")
                    return None, main_content, last_response

                # For plain text, try fallback to raw response (legacy behavior)
                if current_content not in full_raw_response:
                    if log_callback:
                        log_callback("using_raw_response_fallback",
                            "Using raw response as fallback (plain text mode)")
                    all_translations.append(full_raw_response.strip())
                    if last_response:
                        last_response.was_fallback = True
                else:
                    # Response contains input - this is an error
                    if log_callback:
                        log_callback("llm_prompt_in_response_warning",
                            "WARNING: LLM response seems to contain input. Discarded.")
                    return None, main_content, last_response

            # If we had remaining content from a previous split, translate it
            if remaining_content.strip():
                current_content = remaining_content
                remaining_content = ""
                # Update context for continuity
                if all_translations:
                    words = all_translations[-1].split()
                    previous_translation_context = " ".join(words[-25:]) if len(words) > 25 else all_translations[-1]
                reduction_attempt = 0  # Reset for new content
                continue

            # Success - combine all translations
            combined = "\n".join(all_translations) if all_translations else None
            return combined, main_content, last_response

        except RepetitionLoopError as e:
            # Repetition loop detected - this typically happens with thinking models
            # when context window is too small. Try increasing context.
            if context_manager:
                old_context = context_manager.get_context_size()
                # Force a larger context increase for repetition loops
                context_manager.increase_context()
                context_manager.increase_context()  # Double increase for repetition loops
                new_context = context_manager.get_context_size()

                if new_context > old_context:
                    if log_callback:
                        log_callback("repetition_loop_retry",
                            f"🔄 Repetition loop detected! Increasing context from {old_context} to {new_context} tokens")
                    else:
                        tqdm.write(f"\n🔄 Repetition loop - increasing context to {new_context}")
                    continue  # Retry with larger context

            # No context manager or can't increase further
            if log_callback:
                log_callback("repetition_loop_fatal",
                    f"⚠️ Repetition loop detected and cannot recover. "
                    f"Try manually increasing OLLAMA_NUM_CTX. Error: {e}")
            else:
                tqdm.write(f"\n⚠️ Repetition loop detected - increase OLLAMA_NUM_CTX")
            return None, main_content, last_response

        except ContextOverflowError as e:
            # If we have a context manager, try increasing context
            if context_manager and context_manager.should_retry_with_larger_context(True, 0):
                context_manager.increase_context()
                continue  # Retry with larger context

            reduction_attempt += 1

            if reduction_attempt > MAX_CHUNK_REDUCTION_ATTEMPTS:
                if log_callback:
                    log_callback("context_overflow_fatal",
                        f"⚠️ Context overflow: Max reduction attempts ({MAX_CHUNK_REDUCTION_ATTEMPTS}) "
                        f"exceeded. Original error: {e}")
                else:
                    tqdm.write(f"\n⚠️ Context overflow after {MAX_CHUNK_REDUCTION_ATTEMPTS} reduction attempts")
                return None, main_content, last_response

            # Calculate new reduction factor
            reduction_factor = CHUNK_REDUCTION_FACTOR ** reduction_attempt

            if log_callback:
                log_callback("context_overflow_retry",
                    f"⚠️ Context overflow detected! Reducing chunk to {reduction_factor*100:.0f}% "
                    f"(attempt {reduction_attempt}/{MAX_CHUNK_REDUCTION_ATTEMPTS})")
            else:
                tqdm.write(f"\n⚠️ Context overflow - reducing chunk (attempt {reduction_attempt})")

            # Split the content
            first_part, second_part = split_chunk_for_retry(current_content, reduction_factor)

            if len(first_part) < MIN_CHUNK_CHARACTERS and not all_translations:
                # Can't reduce further without losing too much content
                if log_callback:
                    log_callback("context_overflow_fatal",
                        f"⚠️ Cannot reduce chunk further (min size: {MIN_CHUNK_CHARACTERS} chars)")
                return None, main_content, last_response

            current_content = first_part
            # Accumulate remaining content for later
            if second_part.strip():
                remaining_content = second_part + ("\n" + remaining_content if remaining_content else "")

    # Shouldn't reach here normally
    return "\n".join(all_translations) if all_translations else None, main_content, last_response


# Legacy wrapper for backward compatibility

async def generate_translation_request(main_content, context_before, context_after, previous_translation_context,
                                       source_language="English", target_language="Chinese", model=DEFAULT_MODEL,
                                       llm_client=None, log_callback=None, has_placeholders=False,
                                       prompt_options=None, context_manager: AdaptiveContextManager = None,
                                       placeholder_format: Optional[Tuple[str, str]] = None,
                                       runtime_state: Optional[dict] = None):
    """
    Generate translation request to LLM API with automatic context overflow handling.

    Args:
        main_content (str): Text to translate
        context_before (str): Context before main content
        context_after (str): Context after main content
        previous_translation_context (str): Previous translation for consistency
        source_language (str): Source language
        target_language (str): Target language
        model (str): LLM model name
        llm_client: LLM client instance
        log_callback (callable): Logging callback function
        has_placeholders (bool): If True, includes placeholder preservation instructions
        prompt_options (dict): Optional dict with prompt customization options
        context_manager (AdaptiveContextManager): Optional context manager for adaptive retry on overflow
        placeholder_format (Tuple[str, str]): Optional tuple of (prefix, suffix) for placeholders.
            e.g., ('[', ']') for [0] format or ('[[', ']]') for [[0]] format

    Returns:
        str: Translated text or None if failed
    """
    # Skip LLM translation for single character or empty chunks
    if len(main_content.strip()) <= 1:
        if log_callback:
            log_callback("skip_translation", f"Skipping LLM for single/empty character: '{main_content}'")
        return main_content

    # Use the adaptive context handler
    translated_text, _, _ = await _make_llm_request_with_adaptive_context(
        main_content=main_content,
        context_before=context_before,
        context_after=context_after,
        previous_translation_context=previous_translation_context,
        source_language=source_language,
        target_language=target_language,
        model=model,
        llm_client=llm_client,
        log_callback=log_callback,
        has_placeholders=has_placeholders,
        prompt_options=prompt_options,
        context_manager=context_manager,
        placeholder_format=placeholder_format,
        runtime_state=runtime_state,
    )

    if translated_text:
        return translated_text
    else:
        err_msg = "ERROR: LLM API request failed"
        if log_callback:
            log_callback("llm_api_error", err_msg)
        else:
            tqdm.write(f"\n{err_msg}")
        return None



async def _make_refinement_request(
    draft_translation: str,
    context_before: str,
    context_after: str,
    previous_refined_context: str,
    target_language: str,
    model: str,
    llm_client,
    log_callback,
    has_placeholders: bool,
    prompt_options: dict = None,
    context_manager: AdaptiveContextManager = None,
    runtime_state: Optional[dict] = None,
    source_translation: str = "",
) -> Tuple[Optional[str], Optional[LLMResponse]]:
    """
    Make LLM request for refinement pass.

    Similar to translation request but uses the refinement prompt.

    Args:
        draft_translation: First-pass translation to refine
        context_before: Previously refined text for context
        context_after: Text appearing after for context
        previous_refined_context: Last refined text for consistency
        target_language: Target language
        model: LLM model name
        llm_client: LLM client instance
        log_callback: Logging callback function
        has_placeholders: If True, includes placeholder preservation instructions
        prompt_options: Optional dict with prompt customization options
        context_manager: AdaptiveContextManager for context sizing

    Returns:
        Tuple of (refined_text or None, LLMResponse)
    """
    # Extract refinement instructions from prompt_options
    refinement_instructions = prompt_options.get('refinement_instructions', '') if prompt_options else ''

    # Filter the glossary against the SOURCE (plus draft fallback) — Hy-MT2 /
    # Qwen terms are source-language, so names that never survived the first
    # pass still need to hit the glossary during post-editing.
    glossary_block = _build_refinement_glossary_block(
        source_translation, draft_translation, prompt_options,
        log_callback=log_callback, runtime_state=runtime_state,
        target_language=target_language,
    )

    preserve_placeholders = bool(has_placeholders)
    if not preserve_placeholders:
        from src.core.refine.structure import text_has_placeholders
        preserve_placeholders = text_has_placeholders(draft_translation)

    # Generate refinement prompts
    prompt_pair = generate_refinement_prompt(
        draft_translation=draft_translation,
        context_before=context_before,
        context_after=context_after,
        previous_refined_context=previous_refined_context,
        target_language=target_language,
        has_placeholders=preserve_placeholders,
        prompt_options=prompt_options,
        additional_instructions=refinement_instructions,
        glossary_block=glossary_block,
        source_translation=source_translation,
        source_language=(prompt_options or {}).get("source_language", ""),
    )

    client = llm_client or default_client
    last_response: Optional[LLMResponse] = None
    empty_retries = 0

    # Retry loop with adaptive context (mirrors translation logic)
    while True:
        try:
            # Log the request
            if log_callback:
                log_callback("refinement_request", "Sending refinement request to LLM", data={
                    'type': 'refinement_request',
                    'system_prompt': prompt_pair.system,
                    'user_prompt': prompt_pair.user,
                    'model': model
                })

            start_time = time.time()

            # Set context from manager if available
            if context_manager and hasattr(client, 'context_window'):
                new_ctx = context_manager.get_context_size()
                if client.context_window != new_ctx:
                    if log_callback:
                        log_callback("context_update",
                            f"📐 Refinement context window: {client.context_window} → {new_ctx}")
                    client.context_window = new_ctx

            llm_response = await client.make_request(
                prompt_pair.user, model, system_prompt=prompt_pair.system
            )
            execution_time = time.time() - start_time

            if not llm_response:
                return None, None

            last_response = llm_response
            full_raw_response = llm_response.content or ""

            # Truncated empty completions already exhausted provider-side
            # retries (OpenRouter, OpenCode, … CoT ate max_tokens). Extra loops stall
            # 4-pass refine for minutes per chunk; keep the previous draft.
            if not str(full_raw_response).strip() and llm_response.was_truncated:
                if log_callback:
                    log_callback(
                        "empty_llm_response",
                        "⚠️ Empty truncated refinement — keeping the draft translation.",
                    )
                return None, last_response

            # Check if we should retry with larger context (adaptive strategy)
            if context_manager and llm_response.was_truncated:
                if context_manager.should_retry_with_larger_context(
                    llm_response.was_truncated, llm_response.context_used
                ):
                    context_manager.increase_context()
                    continue  # Retry with larger context

            if not str(full_raw_response).strip():
                empty_retries += 1
                tokens = llm_response.completion_tokens or 0
                if empty_retries < MAX_TRANSLATION_ATTEMPTS:
                    delay = min(8, 2 * empty_retries)
                    if log_callback:
                        log_callback("empty_llm_retry",
                            f"⚠️ Empty refinement response ({tokens} completion tokens) — "
                            f"retrying in {delay}s "
                            f"({empty_retries}/{MAX_TRANSLATION_ATTEMPTS})")
                    await asyncio.sleep(delay)
                    continue
                if log_callback:
                    log_callback("empty_llm_response",
                        f"⚠️ Empty refinement response after {empty_retries} attempts "
                        f"({tokens} completion tokens). Keeping the draft translation.")
                return None, last_response

            # Log the response
            if log_callback:
                log_callback("refinement_response", "Refinement response received", data={
                    'type': 'refinement_response',
                    'response': full_raw_response,
                    'execution_time': execution_time,
                    'model': model,
                    'tokens': {
                        'prompt': llm_response.prompt_tokens,
                        'completion': llm_response.completion_tokens,
                        'total': llm_response.context_used,
                        'limit': llm_response.context_limit
                    }
                })

            # Extract refined text (unclosed </TRANSLATION> is salvaged)
            refined_text = client.extract_translation(full_raw_response)
            unclosed = _TAG_INSPECTOR.omitted_closing_tag(full_raw_response)

            if refined_text:
                if unclosed and llm_response.was_truncated:
                    # A cut refine is worse than the previous draft.
                    if log_callback:
                        log_callback(
                            "refinement_truncated",
                            "⚠️ Refinement truncated before </TRANSLATION> — "
                            "keeping the previous draft.",
                        )
                    return None, llm_response
                return refined_text, llm_response
            else:
                empty_retries += 1
                if empty_retries < MAX_TRANSLATION_ATTEMPTS:
                    delay = min(8, 2 * empty_retries)
                    if log_callback:
                        log_callback(
                            "refinement_extraction_retry",
                            f"⚠️ Malformed refinement tags — retrying in {delay}s "
                            f"({empty_retries}/{MAX_TRANSLATION_ATTEMPTS})",
                        )
                    await asyncio.sleep(delay)
                    continue
                # Fallback to raw response if no tags found. Never treat a
                # blank body as a successful refine — that would wipe the draft.
                if full_raw_response.strip() and draft_translation not in full_raw_response:
                    salvaged = _TAG_INSPECTOR.extract(full_raw_response)
                    return (salvaged or full_raw_response.strip()), llm_response
                else:
                    if log_callback:
                        log_callback("refinement_warning",
                            "WARNING: Refinement response contains input. Using original.")
                    return None, llm_response

        except RepetitionLoopError as e:
            # Repetition loop detected - try increasing context (double increase)
            if context_manager:
                old_context = context_manager.get_context_size()
                context_manager.increase_context()
                context_manager.increase_context()  # Double increase for repetition loops
                new_context = context_manager.get_context_size()

                if new_context > old_context:
                    if log_callback:
                        log_callback("refinement_repetition_retry",
                            f"🔄 Refinement repetition loop! Increasing context from {old_context} to {new_context} tokens")
                    continue  # Retry with larger context

            # No context manager or can't increase further
            if log_callback:
                log_callback("refinement_error",
                    f"⚠️ Refinement repetition loop, cannot recover: {e}")
            return None, last_response

        except ContextOverflowError as e:
            # Context overflow - try increasing context
            if context_manager and context_manager.should_retry_with_larger_context(True, 0):
                context_manager.increase_context()
                if log_callback:
                    log_callback("refinement_overflow_retry",
                        f"⚠️ Refinement context overflow! Retrying with context {context_manager.get_context_size()}")
                continue  # Retry with larger context

            # Can't increase further
            if log_callback:
                log_callback("refinement_error",
                    f"⚠️ Refinement context overflow, cannot recover: {e}")
            return None, last_response


async def refine_chunks(
    translated_chunks: List[str],
    original_chunks: List[Dict],
    target_language: str,
    model_name: str,
    api_endpoint: str,
    log_callback=None,
    stats_callback=None,
    check_interruption_callback=None,
    llm_provider="ollama",
    gemini_api_key=None,
    openai_api_key=None,
    openrouter_api_key=None,
    mistral_api_key=None,
    deepseek_api_key=None,
    poe_api_key=None,
    nim_api_key=None,
    anthropic_api_key=None,
    xai_api_key=None,
    opencode_api_key=None,
    opencodego_api_key=None,
    ollamacloud_api_key=None,
    context_window=2048,
    auto_adjust_context=True,
    prompt_options=None,
    checkpoint_manager=None,
    translation_id=None,
    refinement_output_filepath=None,
) -> List[str]:
    """
    Refine translated chunks with a one-pass Automatic Post-Editing pass.

    This function takes already-translated chunks and runs them through a
    Hy-MT2/Chimera APE prompt that post-edits the draft against the source.

    Args:
        translated_chunks: List of translated text strings from first pass
        original_chunks: Original chunk dictionaries (for context structure)
        target_language: Target language name
        model_name: LLM model name
        api_endpoint: API endpoint        log_callback: Logging callback
        stats_callback: Statistics update callback
        check_interruption_callback: Interruption check callback
        llm_provider: LLM provider name
        gemini_api_key: Gemini API key
        openai_api_key: OpenAI API key
        openrouter_api_key: OpenRouter API key
        context_window: Initial context window size
        auto_adjust_context: Enable adaptive context adjustment
        prompt_options: Optional dict with prompt customization options

    Returns:
        List of refined text strings
    """
    from src.core.refine.refinement_checkpoint import (
        clear_one_pass_state,
        load_one_pass_state,
        save_one_pass_state,
    )

    total_chunks = len(translated_chunks)
    start_index, checkpoint_current, _checkpoint_state = load_one_pass_state(
        checkpoint_manager, translation_id, total_segments=total_chunks
    )
    working_chunks = list(translated_chunks)
    if isinstance(checkpoint_current, list) and len(checkpoint_current) == total_chunks:
        working_chunks = list(checkpoint_current)

    refined_parts = list(working_chunks[:start_index])
    last_refined_context = ""
    if refined_parts:
        previous = refined_parts[-1].split()
        last_refined_context = " ".join(previous[-25:]) if len(previous) > 25 else refined_parts[-1]
    # Transient per-job state (e.g. glossary cap warning dedupe) — never persisted.
    runtime_state: dict = {}

    # Single-phase refinement tracker (the workflow phase, when this runs as the
    # second pass of a translate→refine job, is tagged at the handler seam).
    progress_tracker = TokenProgressTracker()
    progress_tracker.start()
    token_counter = TokenChunker(max_tokens=800)
    for chunk_text in translated_chunks:
        token_count = token_counter.count_tokens(chunk_text)
        progress_tracker.register_chunk(token_count)

    if log_callback:
        log_callback("refinement_start", f"✨ Starting refinement pass ({total_chunks} chunks)...")

    # Determine if model is a thinking model for initial context sizing
    is_known_thinking_model = any(tm in model_name.lower() for tm in THINKING_MODELS)

    # Refinement needs MORE context than translation because:
    # - The prompt includes the already-translated text (input)
    # - Plus context before/after
    # - Plus instructions
    # So we start with at least 4096 or the user's context_window, whichever is larger
    REFINEMENT_MIN_CONTEXT = 4096

    if auto_adjust_context:
        if is_known_thinking_model:
            initial_context = max(ADAPTIVE_CONTEXT_INITIAL_THINKING, REFINEMENT_MIN_CONTEXT)
        else:
            initial_context = max(INITIAL_CONTEXT_SIZE * 2, REFINEMENT_MIN_CONTEXT)
    else:
        initial_context = max(context_window, REFINEMENT_MIN_CONTEXT)

    # Create LLM client
    llm_client = create_llm_client(
        llm_provider, gemini_api_key, api_endpoint, model_name,
        openai_api_key=openai_api_key,
        openrouter_api_key=openrouter_api_key,
        mistral_api_key=mistral_api_key,
        deepseek_api_key=deepseek_api_key,
        poe_api_key=poe_api_key,
        nim_api_key=nim_api_key,
        anthropic_api_key=anthropic_api_key,
        xai_api_key=xai_api_key,
        opencode_api_key=opencode_api_key,
        opencodego_api_key=opencodego_api_key,
        ollamacloud_api_key=ollamacloud_api_key,
        context_window=initial_context, log_callback=log_callback
    )

    # Create adaptive context manager for Ollama
    context_manager = None
    if llm_provider == "ollama" and auto_adjust_context:
        from .context_optimizer import MAX_CONTEXT_SIZE
        context_manager = AdaptiveContextManager(
            initial_context=initial_context,
            context_step=CONTEXT_STEP,
            max_context=MAX_CONTEXT_SIZE,
            log_callback=log_callback
        )
        if log_callback:
            log_callback("refinement_context", f"📐 Refinement context: starting at {initial_context} tokens (min for refinement: {REFINEMENT_MIN_CONTEXT})")

    # Detect thinking model status
    if llm_client and llm_provider == "ollama":
        await llm_client.detect_thinking_model()

    try:
        iterator = tqdm(
            enumerate(working_chunks),
            total=total_chunks,
            desc=f"Refining {target_language} translation",
            unit="seg"
        ) if not log_callback else enumerate(working_chunks)

        for i, draft_text in iterator:
            if i < start_index:
                progress_tracker.mark_completed(i, 0)
                continue
            # Check for interruption
            if check_interruption_callback and check_interruption_callback():
                if log_callback:
                    log_callback("refinement_interrupted",
                        f"Refinement interrupted at chunk {i+1}/{total_chunks}")
                else:
                    tqdm.write(f"\nRefinement interrupted at chunk {i+1}/{total_chunks}")
                partial = refined_parts + working_chunks[i:]
                state = save_one_pass_state(
                    checkpoint_manager, translation_id,
                    next_segment=i, total_segments=total_chunks, current=list(partial),
                    output_filepath=refinement_output_filepath, log_callback=log_callback,
                )
                raise RefinementInterrupted(partial_result=list(partial), refinement_state=state)

            # Progress update (token-based)
            # Measure refinement time for this chunk
            chunk_start_time = time.time()

            # Skip empty chunks
            if not draft_text.strip():
                refined_parts.append(draft_text)
                chunk_elapsed = time.time() - chunk_start_time
                progress_tracker.mark_completed(i, chunk_elapsed)
                if stats_callback:
                    stats_callback(progress_tracker.get_stats().to_dict())
                continue

            # Skip very short content
            if len(draft_text.strip()) <= 1:
                refined_parts.append(draft_text)
                chunk_elapsed = time.time() - chunk_start_time
                progress_tracker.mark_completed(i, chunk_elapsed)
                continue

            # Get context from original chunks if available
            context_before = ""
            context_after = ""
            source_translation = ""
            if i < len(original_chunks):
                context_before = original_chunks[i].get("context_before", "")
                context_after = original_chunks[i].get("context_after", "")
                source_translation = original_chunks[i].get("source_text", "") or ""

            # Make refinement request
            try:
                from src.core.refine.structure import text_has_placeholders
                refined_text, llm_response = await _make_refinement_request(
                    draft_translation=draft_text,
                    context_before=context_before,
                    context_after=context_after,
                    previous_refined_context=last_refined_context,
                    target_language=target_language,
                    model=model_name,
                    llm_client=llm_client,
                    log_callback=log_callback,
                    has_placeholders=text_has_placeholders(draft_text),
                    prompt_options=prompt_options,
                    context_manager=context_manager,
                    runtime_state=runtime_state,
                    source_translation=source_translation,
                )
            except RateLimitError as e:
                if log_callback:
                    retry_msg = f" (retry after ~{e.retry_after}s)" if e.retry_after else ""
                    log_callback("rate_limit_pause",
                        f"⏸️ Rate limited by {e.provider or 'API'}{retry_msg}. "
                        f"Auto-pausing refinement at chunk {i+1}/{total_chunks}...")
                # Add remaining unrefined chunks as-is
                for remaining in working_chunks[i:]:
                    refined_parts.append(remaining)
                # Invariant: len(refined_parts) == len(translated_chunks) here —
                # the list is complete, chunks at index >= i are the unrefined
                # drafts. Hand it to the caller so the partial pass can be saved.
                e.partial_result = list(refined_parts)
                e.refinement_state = save_one_pass_state(
                    checkpoint_manager, translation_id,
                    next_segment=i, total_segments=total_chunks,
                    current=list(refined_parts),
                    output_filepath=refinement_output_filepath, log_callback=log_callback,
                )
                raise  # Re-raise to handlers.py

            # Record success in context manager
            if refined_text is not None and llm_response and context_manager:
                context_manager.record_success(
                    prompt_tokens=llm_response.prompt_tokens,
                    completion_tokens=llm_response.completion_tokens,
                    context_limit=llm_response.context_limit
                )

            chunk_elapsed = time.time() - chunk_start_time

            if refined_text is not None:
                # Clean the refined text
                refined_text = clean_translated_text(refined_text)
                from .refine.structure import is_plain_text_structure_safe
                if not is_plain_text_structure_safe(draft_text, refined_text):
                    if log_callback:
                        log_callback(
                            "refinement_structure_rejected",
                            f"⚠️ Refinement changed protected text structure "
                            f"for chunk {i + 1}; keeping the previous valid draft.",
                        )
                    refined_text = draft_text
                refined_parts.append(refined_text)
                progress_tracker.mark_completed(i, chunk_elapsed)

                # Update context for next chunk
                words = refined_text.split()
                if len(words) > 25:
                    last_refined_context = " ".join(words[-25:])
                else:
                    last_refined_context = refined_text
            else:
                # Keep original translation if refinement fails
                if log_callback:
                    log_callback("refinement_chunk_failed",
                        f"Refinement failed for chunk {i+1}, keeping original translation")
                refined_parts.append(draft_text)
                progress_tracker.mark_failed(i)
                last_refined_context = ""

            if stats_callback:
                stats_callback(progress_tracker.get_stats().to_dict())

    finally:
        if llm_client:
            await llm_client.close()

    stats = progress_tracker.get_stats()
    if log_callback:
        log_callback("refinement_complete",
            f"✨ Refinement complete: {stats.completed_chunks} refined, {stats.failed_chunks} kept original")

    clear_one_pass_state(checkpoint_manager, translation_id)
    return refined_parts


# Subtitle translation functions moved to subtitle_translator.py

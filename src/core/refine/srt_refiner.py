"""SRT refine-only mode.

Runs the existing refine_subtitle_translations helper on each subtitle of
an already-translated SRT and writes a polished file. Timestamps and
subtitle indices are preserved verbatim.
"""

import os
import aiofiles
from typing import Optional, Callable, Dict, Any

from src.config import (
    DEFAULT_MODEL,
    API_ENDPOINT,
    SRT_LINES_PER_BLOCK,
)

# Disable the char cap when grouping: block sizing is purely fixed-count
# (every block holds exactly SRT_LINES_PER_BLOCK subtitles).
_NO_CHAR_CAP = 10 ** 12
from src.core.llm_client import create_llm_client
from src.core.srt_processor import SRTProcessor
from src.core.subtitle_translator import refine_subtitle_translations
from src.core.llm.exceptions import RateLimitError, RefinementInterrupted


async def refine_srt_file(
    input_filepath: str,
    output_filepath: str,
    target_language: str,
    source_filepath: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
    cli_api_endpoint: str = API_ENDPOINT,
    log_callback: Optional[Callable] = None,
    stats_callback: Optional[Callable] = None,
    check_interruption_callback: Optional[Callable] = None,
    llm_provider: str = "ollama",
    gemini_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    mistral_api_key: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
    poe_api_key: Optional[str] = None,
    nim_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    xai_api_key: Optional[str] = None,
    opencode_api_key: Optional[str] = None,
    opencodego_api_key: Optional[str] = None,
    ollamacloud_api_key: Optional[str] = None,
    prompt_options: Optional[Dict[str, Any]] = None,
    checkpoint_manager: Any = None,
    translation_id: Optional[str] = None,
    refinement_output_filepath: Optional[str] = None,
) -> bool:
    """Run a refinement-only pass on an already-translated SRT file."""
    if not os.path.exists(input_filepath):
        err_msg = f"ERROR: Input SRT file '{input_filepath}' not found."
        if log_callback:
            log_callback("srt_file_not_found", err_msg)
        return False

    try:
        async with aiofiles.open(input_filepath, 'r', encoding='utf-8') as f:
            srt_content = await f.read()
    except Exception as e:
        if log_callback:
            log_callback("srt_read_error",
                         f"ERROR: Reading SRT file '{input_filepath}': {e}")
        return False

    srt_processor = SRTProcessor()
    if not srt_processor.validate_srt(srt_content):
        if log_callback:
            log_callback("srt_invalid_format", "Invalid SRT file format")
        return False

    subtitles = srt_processor.parse_srt(srt_content)
    if not subtitles:
        if log_callback:
            log_callback("srt_no_subtitles", "No subtitles found in file")
        return False

    source_subtitles = None
    if source_filepath and os.path.abspath(source_filepath) != os.path.abspath(input_filepath):
        try:
            async with aiofiles.open(source_filepath, 'r', encoding='utf-8') as f:
                source_content = await f.read()
            if srt_processor.validate_srt(source_content):
                source_subtitles = srt_processor.parse_srt(source_content)
            else:
                if log_callback:
                    log_callback(
                        "srt_source_read_warning",
                        "⚠️ Original SRT is invalid; refinement will use the translated cues as fallback source.",
                    )
        except Exception as exc:
            if log_callback:
                log_callback(
                    "srt_source_read_warning",
                    f"⚠️ Could not read original SRT for refinement: {exc}",
                )

    if log_callback:
        log_callback("srt_refine_start",
                     f"✨ Refining {len(subtitles)} subtitles in {target_language}...")

    if stats_callback:
        stats_callback({
            'total_chunks': len(subtitles),
            'completed_chunks': 0,
            'failed_chunks': 0,
        })

    # Key translations by list position, NOT by the cue number printed in
    # the file: update_translated_subtitles applies by position, and real
    # files have gaps, restarts or 0-based numbering (issue #205).
    translations: Dict[int, str] = {
        idx: sub.get('text', '') for idx, sub in enumerate(subtitles)
    }
    subtitle_positions = {id(sub): idx for idx, sub in enumerate(subtitles)}

    llm_client = create_llm_client(
        llm_provider, gemini_api_key, cli_api_endpoint, model_name,
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
        log_callback=log_callback,
    )

    # Fixed-count grouping for refine (no char cap): every block sent to
    # the LLM has the same shape, which keeps [N] marker accounting
    # predictable across the whole file.
    refine_blocks = srt_processor.group_subtitles_for_translation(
        subtitles, SRT_LINES_PER_BLOCK, _NO_CHAR_CAP
    )

    try:
        refined = await refine_subtitle_translations(
            translations=translations,
            target_language=target_language,
            model_name=model_name,
            llm_client=llm_client,
            log_callback=log_callback,
            prompt_options=prompt_options,
            post_processing_instructions=(
                prompt_options.get('refinement_instructions', '')
                if prompt_options else ''
            ),
            stats_callback=stats_callback,
            check_interruption_callback=check_interruption_callback,
            subtitle_blocks=refine_blocks,
            subtitle_positions=subtitle_positions,
            source_subtitles=source_subtitles,
            checkpoint_manager=checkpoint_manager,
            translation_id=translation_id,
            refinement_output_filepath=refinement_output_filepath or output_filepath,
        )
    except (RateLimitError, RefinementInterrupted) as exc:
        partial = getattr(exc, 'partial_result', None)
        if isinstance(partial, dict):
            partial_subs = srt_processor.update_translated_subtitles(subtitles, partial)
            try:
                partial_srt = srt_processor.reconstruct_srt(partial_subs)
                async with aiofiles.open(output_filepath, 'w', encoding='utf-8') as f:
                    await f.write(partial_srt)
            except Exception:
                pass
        raise
    finally:
        if llm_client:
            try:
                await llm_client.close()
            except Exception:
                pass

    if check_interruption_callback and check_interruption_callback():
        if log_callback:
            log_callback("srt_refine_interrupted",
                         "Refinement interrupted before save")
        raise RefinementInterrupted(
            "SRT refinement interrupted before save",
            partial_result=refined,
        )

    refined_subs = srt_processor.update_translated_subtitles(subtitles, refined)
    refined_srt = srt_processor.reconstruct_srt(refined_subs)

    try:
        async with aiofiles.open(output_filepath, 'w', encoding='utf-8') as f:
            await f.write(refined_srt)
        if log_callback:
            log_callback("srt_refine_done",
                         f"✅ Refined SRT saved: {output_filepath}")
        return True
    except Exception as e:
        if log_callback:
            log_callback("srt_save_error",
                         f"ERROR: Saving SRT file '{output_filepath}': {e}")
        return False

"""EPUB refine-only mode.

Walks each XHTML content file of an already-translated EPUB, refines its
body in place, and repackages. Phase/segment state is checkpointed so an
interruption resumes without replaying completed refinement calls.
"""

import os
import shutil
import tempfile
from typing import Optional, Callable, Dict, Any, List, Tuple
from lxml import etree

from src.config import (
    DEFAULT_MODEL, API_ENDPOINT, MAX_TOKENS_PER_CHUNK, THINKING_MODELS,
    ADAPTIVE_CONTEXT_INITIAL_THINKING,
)
from src.core.epub.translator import (
    _extract_epub, _parse_epub_manifest, _create_llm_client,
    _create_context_manager, _repackage_epub,
)
from src.core.epub.xhtml_translator import (
    _setup_translation, _preserve_tags, _create_chunks,
    _replace_body, _escape_stray_angle_brackets, _refine_epub_chunks,
)
from src.core.epub.container import TranslationContainer
from src.core.context_optimizer import INITIAL_CONTEXT_SIZE
from .client_setup import build_refine_client
from src.core.llm.exceptions import RateLimitError, RefinementInterrupted


def _globalize_chunk_text(
    chunk: Dict,
    placeholder_format: Tuple[str, str],
) -> str:
    """Convert a chunk's placeholders from local to global indices.

    `_refine_epub_chunks` expects globally-numbered placeholders because it
    re-localizes internally before sending to the LLM. In translate-mode the
    chunks already carry global indices; in refine-only mode they come fresh
    from HtmlChunker with local indices, so we re-globalize here.
    """
    text = chunk['text']
    global_indices = chunk.get('global_indices', [])
    if not global_indices:
        return text

    prefix, suffix = placeholder_format
    for local_idx, global_idx in enumerate(global_indices):
        local_ph = f"{prefix}{local_idx}{suffix}"
        text = text.replace(local_ph, f"__TEMP_GLOBAL_{global_idx}__")
    for global_idx in global_indices:
        text = text.replace(f"__TEMP_GLOBAL_{global_idx}__",
                            f"{prefix}{global_idx}{suffix}")
    return text


async def _refine_one_xhtml(
    doc_root: etree._Element,
    target_language: str,
    model_name: str,
    llm_client: Any,
    max_tokens_per_chunk: int,
    log_callback: Optional[Callable],
    context_manager: Optional[Any],
    prompt_options: Optional[Dict],
    check_interruption_callback: Optional[Callable],
    container: Optional[TranslationContainer] = None,
    source_doc_root: Optional[etree._Element] = None,
    checkpoint_manager: Optional[Any] = None,
    translation_id: Optional[str] = None,
    checkpoint_scope: str = "global",
    refinement_output_filepath: Optional[str] = None,
) -> bool:
    """Refine a single parsed XHTML document in place."""
    body_html, body_element, tag_preserver = _setup_translation(
        doc_root, log_callback, container
    )
    if not body_html or body_element is None:
        if log_callback:
            log_callback("no_body", "No <body> element found")
        return False

    text_with_placeholders, global_tag_map, placeholder_format = _preserve_tags(
        body_html, tag_preserver, log_callback, protect_technical=True
    )

    chunks = _create_chunks(
        text_with_placeholders, global_tag_map, max_tokens_per_chunk,
        log_callback, container,
    )

    if not chunks:
        if log_callback:
            log_callback("no_chunks", "No translatable chunks in this XHTML, skipping")
        return True

    draft_globalized = [_globalize_chunk_text(c, placeholder_format) for c in chunks]

    source_chunks = None
    if source_doc_root is not None:
        source_body_html, source_body_element, source_tag_preserver = _setup_translation(
            source_doc_root, log_callback, container
        )
        if source_body_html and source_body_element is not None:
            source_text_with_placeholders, source_global_tag_map, _ = _preserve_tags(
                source_body_html, source_tag_preserver, log_callback, protect_technical=True
            )
            source_chunks = _create_chunks(
                source_text_with_placeholders,
                source_global_tag_map,
                max_tokens_per_chunk,
                log_callback,
                container,
            )
            if len(source_chunks) != len(chunks):
                if log_callback:
                    log_callback(
                        "epub_source_alignment_warning",
                        f"⚠️ Source/translation chunk count differs ({len(source_chunks)} vs {len(chunks)}); "
                        "using monotonic source mapping.",
                    )
                if source_chunks:
                    source_chunks = [
                        source_chunks[min(
                            len(source_chunks) - 1,
                            int(index * len(source_chunks) / len(chunks)),
                        )]
                        for index in range(len(chunks))
                    ]
                else:
                    source_chunks = None

    try:
        refined_chunks = await _refine_epub_chunks(
            translated_chunks=draft_globalized,
            chunks=chunks,
            target_language=target_language,
            model_name=model_name,
            llm_client=llm_client,
            context_manager=context_manager,
            placeholder_format=placeholder_format,
            log_callback=log_callback,
            prompt_options=prompt_options,
            source_chunks=source_chunks,
            check_interruption_callback=check_interruption_callback,
            checkpoint_manager=checkpoint_manager,
            translation_id=translation_id,
            checkpoint_scope=checkpoint_scope,
            refinement_output_filepath=refinement_output_filepath,
        )
    except (RateLimitError, RefinementInterrupted) as exc:
        partial_chunks = getattr(exc, "partial_result", None)
        if partial_chunks and len(partial_chunks) == len(chunks):
            partial_text = _escape_stray_angle_brackets(''.join(partial_chunks))
            partial_html = tag_preserver.restore_tags(partial_text, global_tag_map)
            _replace_body(body_element, partial_html, log_callback)
        raise

    if check_interruption_callback and check_interruption_callback():
        if log_callback:
            log_callback("refine_interrupted",
                         "Refinement interrupted before reconstruction")
        return False

    full_text = ''.join(refined_chunks)
    full_text = _escape_stray_angle_brackets(full_text)
    final_html = tag_preserver.restore_tags(full_text, global_tag_map)

    return _replace_body(body_element, final_html, log_callback)


async def refine_epub_file(
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
    nexum_api_key: Optional[str] = None,
    context_window: int = 2048,
    auto_adjust_context: bool = True,
    prompt_options: Optional[Dict] = None,
    max_tokens_per_chunk: int = MAX_TOKENS_PER_CHUNK,
    checkpoint_manager: Optional[Any] = None,
    translation_id: Optional[str] = None,
    refinement_output_filepath: Optional[str] = None,
) -> bool:
    """Run a refinement-only pass on an already-translated EPUB."""
    if not os.path.exists(input_filepath):
        err_msg = f"ERROR: Input EPUB file '{input_filepath}' not found."
        if log_callback:
            log_callback("epub_input_file_not_found", err_msg)
        return False

    llm_client, context_manager = build_refine_client(
        model_name=model_name,
        llm_provider=llm_provider,
        cli_api_endpoint=cli_api_endpoint,
        auto_adjust_context=auto_adjust_context,
        context_window=context_window,
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        openrouter_api_key=openrouter_api_key,
        mistral_api_key=mistral_api_key,
        deepseek_api_key=deepseek_api_key,
        poe_api_key=poe_api_key,
        nim_api_key=nim_api_key,
        anthropic_api_key=anthropic_api_key,
        xai_api_key=xai_api_key,
        nexum_api_key=nexum_api_key,
        log_callback=log_callback,
    )
    if llm_client is None:
        return False

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            _extract_epub(input_filepath, temp_dir, log_callback)
            manifest_data = _parse_epub_manifest(temp_dir, log_callback)

            source_opf_dir = None
            source_temp_dir = None
            if (
                source_filepath
                and os.path.abspath(source_filepath) != os.path.abspath(input_filepath)
                and os.path.exists(source_filepath)
            ):
                source_temp_dir = os.path.join(temp_dir, "__source")
                os.makedirs(source_temp_dir, exist_ok=True)
                try:
                    _extract_epub(source_filepath, source_temp_dir, log_callback)
                    source_manifest = _parse_epub_manifest(source_temp_dir, log_callback)
                    source_opf_dir = source_manifest['opf_dir']
                except Exception as exc:
                    source_opf_dir = None
                    if log_callback:
                        log_callback(
                            "epub_source_read_warning",
                            f"⚠️ Could not read original EPUB for refinement: {exc}; "
                            "using translated content as anchor.",
                        )
            elif source_filepath and not os.path.exists(source_filepath) and log_callback:
                log_callback(
                    "epub_source_read_warning",
                    f"⚠️ Original EPUB source not found: {source_filepath}; using translated content as anchor.",
                )

            content_files: List[str] = manifest_data['content_files']
            opf_dir: str = manifest_data['opf_dir']

            total_files = len(content_files)
            if log_callback:
                log_callback("epub_refine_start",
                             f"✨ Starting EPUB refine pass over {total_files} content files...")

            if stats_callback:
                stats_callback({'total_chunks': total_files, 'completed_chunks': 0, 'failed_chunks': 0})

            completed, failed, interrupted = 0, 0, False
            interruption_error = None
            global_state = None
            completed_hrefs = set()
            if checkpoint_manager and translation_id:
                try:
                    global_state = checkpoint_manager.load_refinement_state(
                        translation_id, scope="global"
                    )
                    completed_hrefs = set((global_state or {}).get("completed_hrefs", []))
                except Exception:
                    global_state = None
            for idx, href in enumerate(content_files):
                if href in completed_hrefs:
                    completed += 1
                    continue
                if check_interruption_callback and check_interruption_callback():
                    if log_callback:
                        log_callback("epub_refine_interrupted",
                                     f"Refinement interrupted at file {idx + 1}/{total_files}")
                    interrupted = True
                    interruption_error = RefinementInterrupted(
                        "EPUB refinement interrupted",
                        refinement_state=global_state,
                    )
                    break

                if checkpoint_manager and translation_id:
                    try:
                        checkpoint_manager.save_refinement_state(
                            translation_id,
                            {
                                "version": 1,
                                "phase": 1,
                                "next_segment": 0,
                                "total_segments": total_files,
                                "completed_hrefs": sorted(completed_hrefs),
                                "current_href": href,
                                "output_filepath": output_filepath,
                                "format": "epub",
                            },
                            scope="global",
                        )
                    except Exception:
                        pass

                file_path = os.path.join(opf_dir, href)
                if not os.path.exists(file_path):
                    if log_callback:
                        log_callback("epub_refine_missing",
                                     f"⚠️ Content file missing in EPUB: {href}, skipping")
                    failed += 1
                    continue

                if log_callback:
                    log_callback("epub_refine_file",
                                 f"📄 Refining file {idx + 1}/{total_files}: {href}")

                try:
                    parser = etree.XMLParser(recover=True, remove_blank_text=False)
                    tree = etree.parse(file_path, parser)
                    doc_root = tree.getroot()
                except Exception as e:
                    if log_callback:
                        log_callback("epub_refine_parse_error",
                                     f"⚠️ Could not parse {href}: {e}")
                    failed += 1
                    continue

                source_doc_root = None
                if source_opf_dir:
                    source_file_path = os.path.join(source_opf_dir, href)
                    if os.path.exists(source_file_path):
                        try:
                            source_tree = etree.parse(source_file_path, parser)
                            source_doc_root = source_tree.getroot()
                        except Exception as exc:
                            if log_callback:
                                log_callback(
                                    "epub_source_parse_warning",
                                    f"⚠️ Could not parse source XHTML {href}: {exc}",
                                )

                try:
                    ok = await _refine_one_xhtml(
                        doc_root=doc_root,
                        target_language=target_language,
                        model_name=model_name,
                        llm_client=llm_client,
                        max_tokens_per_chunk=max_tokens_per_chunk,
                        log_callback=log_callback,
                        context_manager=context_manager,
                        prompt_options=prompt_options,
                        check_interruption_callback=check_interruption_callback,
                        source_doc_root=source_doc_root,
                        checkpoint_manager=checkpoint_manager,
                        translation_id=translation_id,
                        checkpoint_scope=f"epub:{href}",
                        refinement_output_filepath=refinement_output_filepath or output_filepath,
                    )
                except (RateLimitError, RefinementInterrupted) as exc:
                    interruption_error = exc
                    interrupted = isinstance(exc, RefinementInterrupted)
                    # Rate limits also produce a usable partial EPUB; preserve
                    # it before the handler applies its pause policy.
                    try:
                        tree.write(file_path, xml_declaration=True,
                                   encoding='utf-8', method='xml')
                    except Exception:
                        pass
                    break

                if ok:
                    try:
                        tree.write(file_path, xml_declaration=True,
                                   encoding='utf-8', method='xml')
                    except Exception as e:
                        if log_callback:
                            log_callback("epub_refine_write_error",
                                         f"⚠️ Could not write refined XHTML {href}: {e}")
                        failed += 1
                        continue
                    completed += 1
                    completed_hrefs.add(href)
                    if checkpoint_manager and translation_id:
                        try:
                            checkpoint_manager.save_refinement_state(
                                translation_id,
                                {
                                    "version": 1,
                                    "phase": 1,
                                    "next_segment": 0,
                                    "total_segments": total_files,
                                    "completed_hrefs": sorted(completed_hrefs),
                                    "output_filepath": output_filepath,
                                    "format": "epub",
                                },
                                scope="global",
                            )
                        except Exception:
                            pass
                else:
                    failed += 1

                if stats_callback:
                    stats_callback({
                        'total_chunks': total_files,
                        'completed_chunks': completed + failed,
                        'failed_chunks': failed,
                    })

            from src.utils.file_utils import get_partial_output_path
            final_output = (
                get_partial_output_path(output_filepath) if interrupted
                else output_filepath
            )
            # The original EPUB is extracted under a private comparison
            # directory. Never include that source copy in the packaged output.
            if source_temp_dir and os.path.exists(source_temp_dir):
                shutil.rmtree(source_temp_dir, ignore_errors=True)
            _repackage_epub(temp_dir=temp_dir,
                            output_filepath=final_output,
                            log_callback=log_callback)

            if interruption_error is not None:
                state = getattr(interruption_error, "refinement_state", None) or {}
                state.update({
                    "version": 1,
                    "phase": state.get("phase", 1),
                    "next_segment": state.get("next_segment", 0),
                    "total_segments": total_files,
                    "completed_hrefs": sorted(completed_hrefs),
                    "current_href": state.get("current_href"),
                    "output_filepath": final_output,
                    "format": "epub",
                })
                interruption_error.refinement_state = state
                raise interruption_error

            if log_callback:
                log_callback("epub_refine_done",
                             f"✅ EPUB refine complete: {completed} files refined, "
                             f"{failed} failed, output: {final_output}")
            return not interrupted and failed == 0
    finally:
        if llm_client and hasattr(llm_client, 'close'):
            try:
                await llm_client.close()
            except Exception:
                pass

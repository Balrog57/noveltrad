"""Refine+ multi-pass Automatic Post-Editing (4 LLM calls + auto QA).

Pass 1: Hy-MT2/Chimera faithful APE (existing prompt + SO constraints)
Auto QA: numbers, entities, placeholders
Pass 2: stylistic fluency
Pass 3: glossary enforcement (skipped when no hits)
Pass 4: grammar / typography
At most one targeted extra LLM call when heuristics fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from src.config import TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT
from src.core.glossary.filter import filter_glossary
from src.core.llm.utils.extraction import TranslationExtractor
from src.core.post_processor import clean_translated_text
from src.core.refine.quality_checks import (
    ACCEPT,
    RETRY_OMISSION,
    RETRY_PASS1,
    RETRY_PASS2,
    RETRY_PASS3,
    QualityReport,
    decide_retry,
    evaluate_pair,
    format_decision_log,
    glossary_terms_from_options,
)
from src.core.refine.structure import is_plain_text_structure_safe, text_has_placeholders
from src.prompts.prompts import (
    PASS1_PLUS_FAITHFUL_INSTRUCTIONS,
    PromptPair,
    extract_json_object,
    generate_glossary_enforcement_prompt,
    generate_grammar_postedit_prompt,
    generate_omission_qa_prompt,
    generate_refinement_prompt,
    generate_style_refinement_prompt,
    published_text_from_payload,
    strip_ambiguity_markers,
)

TEMP_PASS1 = 0.2
TEMP_PASS2 = 0.5
TEMP_PASS3 = 0.2
TEMP_PASS4 = 0.2
TEMP_EXTRA = 0.2

_TAG_INSPECTOR = TranslationExtractor(TRANSLATE_TAG_IN, TRANSLATE_TAG_OUT)

LLMGenerate = Callable[..., Awaitable[Optional[str]]]
StructureGuard = Callable[[str, str], bool]
LogCallback = Optional[Callable[..., Any]]


@dataclass
class PlusPassResult:
    text: str
    report: Optional[QualityReport] = None
    extra_used: bool = False
    llm_calls: int = 0
    skipped_glossary: bool = False
    logs: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.logs is None:
            self.logs = []


def _extract_body(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    extracted = _TAG_INSPECTOR.extract(text)
    body = (extracted or text).strip()
    return body or None


def _accept_candidate(
    previous: str,
    candidate: Optional[str],
    *,
    structure_guard: Optional[StructureGuard],
) -> str:
    if candidate is None:
        return previous
    cleaned = strip_ambiguity_markers(clean_translated_text(candidate) or candidate)
    if not cleaned.strip():
        return previous
    guard = structure_guard or is_plain_text_structure_safe
    if not guard(previous, cleaned):
        return previous
    return cleaned


def _literary_register(prompt_options: Optional[dict]) -> str:
    opts = prompt_options or {}
    instructions = (opts.get("refinement_instructions") or "").strip()
    if instructions:
        first = instructions.splitlines()[0].strip()
        if 0 < len(first) <= 80:
            return first
    return "literary"


def _language_variant(prompt_options: Optional[dict], target_language: str) -> str:
    opts = prompt_options or {}
    code = str(opts.get("target_language_code") or "").strip()
    return code or target_language


def _glossary_pairs(source: str, draft: str, prompt_options: Optional[dict]) -> List[Tuple[str, str]]:
    terms = glossary_terms_from_options(prompt_options)
    lookup = "\n".join(part for part in (source or "", draft or "") if part.strip())
    if not terms or not lookup:
        return []
    filtered, _capped = filter_glossary(lookup, terms)
    return list(filtered.items())


def _heuristic_notes(report: QualityReport) -> str:
    parts: List[str] = []
    if report.missing_numbers:
        parts.append("Missing numbers/dates: " + ", ".join(report.missing_numbers))
    if report.extra_numbers:
        parts.append("Added numbers: " + ", ".join(report.extra_numbers))
    if report.missing_glossary:
        parts.append("Glossary misses: " + ", ".join(report.missing_glossary))
    if report.leftover_source_script:
        parts.append("Untranslated source-script span in the target.")
    return "\n".join(parts)


async def _llm_text(
    llm_generate: LLMGenerate,
    prompt_pair: PromptPair,
    temperature: float,
) -> Optional[str]:
    raw = await llm_generate(prompt_pair, temperature=temperature)
    return _extract_body(raw)


async def _llm_json_text(
    llm_generate: LLMGenerate,
    prompt_pair: PromptPair,
    temperature: float,
    *json_keys: str,
    fallback_previous: str,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    raw = await llm_generate(prompt_pair, temperature=temperature)
    body = _extract_body(raw)
    payload = extract_json_object(body or raw or "")
    if payload is None:
        # Unparseable JSON must not leak notes/omissions into the book.
        # Plain tagged prose (no leading '{') is still accepted as a translation.
        if body and body.strip() and not body.strip().startswith("{"):
            published = strip_ambiguity_markers(body)
            return published or fallback_previous, payload
        return fallback_previous, payload
    published = published_text_from_payload(
        payload, *json_keys, fallback=fallback_previous,
    )
    return published or fallback_previous, payload


async def refine_plus_segment(
    *,
    draft: str,
    source: str = "",
    context_before: str = "",
    context_after: str = "",
    previous_refined_context: str = "",
    target_language: str = "English",
    prompt_options: Optional[dict] = None,
    llm_generate: LLMGenerate,
    structure_guard: Optional[StructureGuard] = None,
    log_callback: LogCallback = None,
    start_pass: int = 1,
    extra_used: bool = False,
    current_text: Optional[str] = None,
    on_pass_complete: Optional[Callable[[int, str, bool], Any]] = None,
    segment_index: int = 1,
) -> PlusPassResult:
    """Run Refine+ on one segment. ``start_pass`` is the next pass to execute."""
    prompt_options = prompt_options or {}
    current = current_text if current_text is not None else draft
    initial = draft
    llm_calls = 0
    skipped_glossary = False
    logs: List[Dict[str, Any]] = []
    last_report: Optional[QualityReport] = None
    register = _literary_register(prompt_options)
    variant = _language_variant(prompt_options, target_language)
    source_language = str(prompt_options.get("source_language") or "")
    refinement_instructions = str(prompt_options.get("refinement_instructions") or "")
    glossary_terms = glossary_terms_from_options(prompt_options)
    has_ph = text_has_placeholders(draft) or text_has_placeholders(source)

    def _log(event: str, message: str, data: Optional[dict] = None) -> None:
        logs.append({"event": event, "message": message, "data": data or {}})
        if log_callback:
            if data is not None:
                log_callback(event, message, data=data)
            else:
                log_callback(event, message)

    async def _advance(next_pass: int, text: str, used_extra: bool) -> None:
        if not on_pass_complete:
            return
        recent = logs[-8:]
        try:
            maybe = on_pass_complete(
                next_pass, text, used_extra, last_report, recent,
            )
        except TypeError:
            maybe = on_pass_complete(next_pass, text, used_extra)
        if hasattr(maybe, "__await__"):
            await maybe

    async def _run_pass1(text: str) -> str:
        nonlocal llm_calls
        extra_instr = PASS1_PLUS_FAITHFUL_INSTRUCTIONS
        if refinement_instructions.strip():
            extra_instr = f"{extra_instr} {refinement_instructions.strip()}"
        pairs = _glossary_pairs(source, text, prompt_options)
        glossary_block = ""
        if pairs:
            glossary_block = "\n".join(f"  - {s} -> {t}" for s, t in pairs)
        prompt = generate_refinement_prompt(
            draft_translation=text,
            context_before=context_before,
            context_after=context_after,
            previous_refined_context=previous_refined_context,
            target_language=target_language,
            has_placeholders=has_ph,
            prompt_options=prompt_options,
            additional_instructions=extra_instr,
            glossary_block=glossary_block,
            source_translation=source,
            initial_translation=initial,
            source_language=source_language,
        )
        candidate = await _llm_text(llm_generate, prompt, TEMP_PASS1)
        llm_calls += 1
        return _accept_candidate(text, candidate, structure_guard=structure_guard)

    async def _run_pass2(text: str) -> str:
        nonlocal llm_calls
        pairs = _glossary_pairs(source, text, prompt_options)
        glossary_block = "\n".join(f"{s} -> {t}" for s, t in pairs)
        prompt = generate_style_refinement_prompt(
            translation=text,
            target_language=target_language,
            source_language=source_language,
            source_text=source,
            register=register,
            glossary_block=glossary_block,
            additional_instructions=refinement_instructions,
            prompt_options=prompt_options,
        )
        candidate = await _llm_text(llm_generate, prompt, TEMP_PASS2)
        llm_calls += 1
        return _accept_candidate(text, candidate, structure_guard=structure_guard)

    async def _run_pass3(text: str) -> Tuple[str, bool]:
        nonlocal llm_calls
        pairs = _glossary_pairs(source, text, prompt_options)
        if not pairs:
            return text, True
        prompt = generate_glossary_enforcement_prompt(
            translation=text,
            glossary_pairs=pairs,
            target_language=target_language,
            source_text=source,
        )
        candidate, payload = await _llm_json_text(
            llm_generate, prompt, TEMP_PASS3, "translation",
            fallback_previous=text,
        )
        llm_calls += 1
        accepted = _accept_candidate(text, candidate, structure_guard=structure_guard)
        if payload:
            _log(
                "refine_plus_glossary_json",
                f"Refine+ glossary changes on segment {segment_index}",
                data={
                    "changes": payload.get("changes") or [],
                    "conflicts": payload.get("conflicts") or [],
                },
            )
        return accepted, False

    async def _run_pass4(text: str) -> str:
        nonlocal llm_calls
        prompt = generate_grammar_postedit_prompt(
            translation=text,
            target_language=target_language,
            variant=variant,
        )
        candidate, payload = await _llm_json_text(
            llm_generate, prompt, TEMP_PASS4, "final", "translation",
            fallback_previous=text,
        )
        llm_calls += 1
        accepted = _accept_candidate(text, candidate, structure_guard=structure_guard)
        if payload:
            _log(
                "refine_plus_grammar_json",
                f"Refine+ grammar edits on segment {segment_index}",
                data={"edits": payload.get("edits") or []},
            )
        return accepted

    async def _run_extra(text: str, kind: str, report: QualityReport) -> str:
        nonlocal llm_calls
        if kind == RETRY_PASS1:
            return await _run_pass1(text)
        if kind == RETRY_PASS2:
            return await _run_pass2(text)
        if kind == RETRY_PASS3:
            nxt, _skipped = await _run_pass3(text)
            return nxt
        notes = _heuristic_notes(report)
        prompt = generate_omission_qa_prompt(
            source_text=source or text,
            translation=text,
            target_language=target_language,
            heuristic_notes=notes,
        )
        candidate, payload = await _llm_json_text(
            llm_generate, prompt, TEMP_EXTRA, "translation", "final",
            fallback_previous=text,
        )
        llm_calls += 1
        if payload:
            _log(
                "refine_plus_omission_json",
                f"Refine+ omission QA on segment {segment_index}",
                data={
                    "omissions": payload.get("omissions") or [],
                    "additions": payload.get("additions") or [],
                },
            )
        return _accept_candidate(text, candidate, structure_guard=structure_guard)

    if start_pass <= 1:
        current = await _run_pass1(current)
        last_report = evaluate_pair(
            source, current, previous=draft,
            glossary_terms=glossary_terms,
            target_language=target_language,
        )
        _log(
            "refine_plus_qa",
            format_decision_log(segment_index, "pass1", ACCEPT, last_report),
            data=last_report.to_log_dict(),
        )
        if not last_report.fidelity_ok() and not extra_used:
            kind = RETRY_OMISSION if source.strip() else RETRY_PASS1
            extra_used = True
            current = await _run_extra(current, kind, last_report)
            _log(
                "refine_plus_extra",
                f"Refine+ extra after pass 1 on segment {segment_index}: {kind}",
            )
        await _advance(2, current, extra_used)

    if start_pass <= 2:
        current = await _run_pass2(current)
        await _advance(3, current, extra_used)

    if start_pass <= 3:
        current, skipped_glossary = await _run_pass3(current)
        await _advance(4, current, extra_used)

    if start_pass <= 4:
        current = await _run_pass4(current)
        await _advance(5, current, extra_used)

    last_report = evaluate_pair(
        source, current, previous=draft,
        glossary_terms=glossary_terms,
        target_language=target_language,
    )
    decision = decide_retry(last_report, extra_used=extra_used)
    _log(
        "refine_plus_eval",
        format_decision_log(segment_index, "final", decision, last_report),
        data=last_report.to_log_dict(),
    )
    if decision != ACCEPT and not extra_used:
        extra_used = True
        current = await _run_extra(current, decision, last_report)
        last_report = evaluate_pair(
            source, current, previous=draft,
            glossary_terms=glossary_terms,
            target_language=target_language,
        )
        await _advance(6, current, extra_used)

    return PlusPassResult(
        text=current,
        report=last_report,
        extra_used=extra_used,
        llm_calls=llm_calls,
        skipped_glossary=skipped_glossary,
        logs=logs,
    )


def is_refine_plus_enabled(prompt_options: Optional[dict]) -> bool:
    return bool(prompt_options and prompt_options.get("refine_plus"))


def make_plus_llm_generate(llm_client, model_name: str) -> LLMGenerate:
    """Adapt ``llm_client.make_request`` to the Refine+ generate callable."""

    async def _generate(prompt_pair: PromptPair, *, temperature: float = None) -> Optional[str]:
        if not llm_client:
            return None
        response = await llm_client.make_request(
            prompt_pair.user,
            model_name,
            system_prompt=prompt_pair.system,
            temperature=temperature,
        )
        if not response:
            return None
        return response.content

    return _generate

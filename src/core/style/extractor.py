"""
Style extraction (Phase 3 of the style-extraction plan).

Turns a raw LLM response into a validated, size-capped list of style rules.
Mirrors the shape of `src.core.glossary.ner`: a permissive parser plus a
thin async wrapper that builds the prompt and calls the provider.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.glossary.ner import find_balanced, strip_thinking_blocks, try_repair_json
from src.core.style.dimensions import ALLOWED_DIMENSIONS, DEFAULT_DIMENSION
from src.core.style.lint import lint_instruction

logger = logging.getLogger("style.extractor")

MAX_RULES = 40
MAX_INSTRUCTION_CHARS = 500
MAX_EVIDENCE_CHARS = 200
MAX_CONTEXT_CHARS = 600

STYLE_TAG_IN = "<STYLE_JSON>"
STYLE_TAG_OUT = "</STYLE_JSON>"


def _empty_result() -> Dict[str, Any]:
    return {"summary": "", "suggested_name": "extracted_style", "context": "", "rules": []}


def parse_style_response(raw: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Permissive parser for style-extraction output.

    Tries, in order:
      1. Content between <STYLE_JSON>...</STYLE_JSON> tags.
      2. Content inside the first markdown ```json fence.
      3. The first balanced {...} JSON object.
      4. The first balanced [...] JSON array (accepted as the `rules` list).

    `context` (the narrative-setting field) is stripped, defaults to "" when
    absent, and is truncated to MAX_CONTEXT_CHARS with a warning when it
    overflows. Unlike `instruction`, it is never passed through
    `lint_instruction`: a setting is descriptive by design and legitimately
    names eras and technology levels.

    Never raises. Returns ({"summary", "suggested_name", "context", "rules"}, warnings).
    """
    if not raw:
        return _empty_result(), ["empty LLM response"]

    text = strip_thinking_blocks(raw).strip()
    warnings: List[str] = []

    payload = _extract_payload(text, warnings)
    if payload is None:
        return _empty_result(), warnings + ["could not locate any JSON payload in response"]

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        repaired = try_repair_json(payload)
        if repaired is None:
            return _empty_result(), warnings + [f"json parse error: {e}"]
        try:
            data = json.loads(repaired)
            warnings.append("json was repaired before parsing (trailing comma or similar)")
        except json.JSONDecodeError as e2:
            return _empty_result(), warnings + [f"json parse error after repair: {e2}"]

    if isinstance(data, list):
        warnings.append("response root is a bare JSON array — treated as 'rules' list")
        summary = ""
        suggested_name = "extracted_style"
        context = ""
        raw_rules: Any = data
    elif isinstance(data, dict):
        summary = _str(data.get("summary"))
        suggested_name = _slugify(_str(data.get("suggested_name")))
        context = _str(data.get("context"))
        raw_rules = data.get("rules")
        if not isinstance(raw_rules, list):
            warnings.append("response object has no usable 'rules' list")
            raw_rules = []
    else:
        return _empty_result(), warnings + [f"unexpected JSON root type: {type(data).__name__}"]

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS].rstrip()
        warnings.append(f"truncated context to {MAX_CONTEXT_CHARS} characters")

    rules, rule_warnings = _normalize_rules(raw_rules)
    warnings.extend(rule_warnings)

    return {
        "summary": summary,
        "suggested_name": suggested_name or "extracted_style",
        "context": context,
        "rules": rules,
    }, warnings


async def extract_style(
    text: str,
    mode: str,
    source_language: str,
    target_language: str,
    llm_provider,
    max_chars: int = 10000,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Run the style-extraction prompt against `text` (truncated to
    `max_chars`) using the given provider. Returns (style, warnings) — see
    `parse_style_response` for the shape of `style`.
    """
    from src.prompts.prompts import generate_style_extraction_prompt

    sample = text[:max_chars] if max_chars and len(text) > max_chars else text
    prompt = generate_style_extraction_prompt(sample, mode, source_language, target_language)

    response = await llm_provider.generate(prompt.user, system_prompt=prompt.system)
    if response is None:
        return _empty_result(), ["LLM returned no response"]

    raw = getattr(response, "content", None) or str(response)
    style, warnings = parse_style_response(raw)

    if not style["rules"]:
        snippet = (raw or "").strip().replace("\n", " ")[:400]
        logger.info(
            "style extraction returned 0 rules (mode=%s, sample_chars=%d, response_chars=%d): %s",
            mode, len(sample), len(raw or ""), snippet,
        )
        if "LLM returned no usable style rules" not in warnings:
            warnings.append("LLM returned no usable style rules")

    return style, warnings


def _extract_payload(text: str, warnings: List[str]) -> Optional[str]:
    tag_match = re.search(
        re.escape(STYLE_TAG_IN) + r"\s*(.*?)\s*" + re.escape(STYLE_TAG_OUT),
        text,
        flags=re.DOTALL,
    )
    if tag_match:
        return tag_match.group(1).strip()

    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        warnings.append("STYLE_JSON tags missing — extracted from markdown code fence")
        return fence_match.group(1).strip()

    # Pick whichever balanced container appears FIRST. A bare array of rule
    # objects (the common case) starts with '[' before its first item's '{',
    # so checking positions — rather than always trying '{' first — avoids
    # matching only that first item and silently dropping the rest.
    obj_pos = text.find("{")
    arr_pos = text.find("[")

    if obj_pos != -1 and (arr_pos == -1 or obj_pos < arr_pos):
        obj = find_balanced(text, "{", "}")
        if obj:
            warnings.append("STYLE_JSON tags missing — extracted balanced JSON object")
            return obj

    if arr_pos != -1:
        array = find_balanced(text, "[", "]")
        if array:
            warnings.append("STYLE_JSON tags missing — extracted balanced JSON array")
            return array

    if obj_pos != -1:
        obj = find_balanced(text, "{", "}")
        if obj:
            warnings.append("STYLE_JSON tags missing — extracted balanced JSON object")
            return obj

    return None


def _normalize_rules(raw_rules: List[Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    rules: List[Dict[str, Any]] = []
    seen: set = set()

    for index, entry in enumerate(raw_rules, start=1):
        if not isinstance(entry, dict):
            continue

        dimension = _str(entry.get("dimension")).lower()
        if dimension not in ALLOWED_DIMENSIONS:
            original = dimension or "(empty)"
            dimension = DEFAULT_DIMENSION
            warnings.append(f"unknown dimension '{original}' for rule {index} (mapped to 'other')")

        instruction = _str(entry.get("instruction"))
        if not instruction:
            warnings.append("skipped rule without 'instruction'")
            continue
        if len(instruction) > MAX_INSTRUCTION_CHARS:
            instruction = _truncate_instruction(instruction)
            warnings.append(f"truncated instruction for rule {index} to {MAX_INSTRUCTION_CHARS} characters")

        evidence = _str(entry.get("evidence"))[:MAX_EVIDENCE_CHARS]

        key = instruction.casefold()
        if key in seen:
            continue
        seen.add(key)

        rules.append({
            "dimension": dimension,
            "instruction": instruction,
            "evidence": evidence,
            "flags": lint_instruction(instruction),
        })

    if len(rules) > MAX_RULES:
        warnings.append(f"truncated rule list to {MAX_RULES} rules")
        rules = rules[:MAX_RULES]

    return rules, warnings


def _truncate_instruction(instruction: str) -> str:
    cut = instruction[:MAX_INSTRUCTION_CHARS]
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut.rstrip() + "…"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("_", value.lower()).strip("_")[:48]
    return slug or "extracted_style"


def _str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()

"""LangGraph agent nodes + system prompts.

The four system prompts below are reproduced VERBATIM from the CDC (§3, prompts
1-4). The {placeholders} are filled from TranslationState via .format().

Pipeline (CDC §3):
    translator -> proofreader -> glossary -> validator -> END

Each node:
  - builds the prompt from state,
  - calls the LLM (JSON mode for agents 2/3/4, raw text for agent 1),
  - parses the JSON via the Pydantic validators (CDC field names),
  - returns the updated state keys + appends a log line for the UI inspector.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.core.state import TranslationState
from src.core.validators import (
    GlossaryOutput,
    ProofreadOutput,
    ValidatorOutput,
)

# --------------------------------------------------------------------------- #
# System prompts — VERBATIM from CDC §3.
# Single braces in the JSON examples are doubled ({{ }}) so str.format() leaves
# them literal; the real placeholders stay single ({source_lang}).
# --------------------------------------------------------------------------- #

TRANSLATOR_SYSTEM = """\
You are the First-Pass Translator in an advanced multi-agent translation pipeline.

### CORE TASK
Translate the provided SOURCE TEXT from {source_lang} to {target_lang}.

### CRITICAL RULES
1. FIDELITY: Preserve the exact meaning, intent, and factual information of the source text. Do not summarize, add, or omit details.
2. STRUCTURE: Maintain the original formatting (paragraphs, line breaks, bullet points, Markdown taggings).
3. NEUTRALITY: Do not attempt to over-polish or hyper-stylize the output at this stage. Aim for a accurate, natural baseline translation.
4. ISOLATION: Output ONLY the translated text. Do not add introductory phrases, notes, or explanations.

### INPUT
- Source Language: {source_lang}
- Target Language: {target_lang}
- Desired Tone/Register: {tone}
- Source Text:
{source_text}

### OUTPUT FORMAT
Provide only the raw translated text in {target_lang}.
"""

PROOFREADER_SYSTEM = """\
You are the Expert Proofreader and Linguist in a multi-agent translation pipeline.

### CORE TASK
Review and refine the draft translation ({draft_translation}) from {source_lang} into {target_lang}, ensuring flawless grammar, idiomatic phrasing, and high readability.

### CRITICAL RULES
1. LINGUISTIC ACCURACY: Fix all grammatical errors, typos, awkward sentence structures, and improper punctuation.
2. NATURAL FLUENCY: Adjust phrases so they sound like native {target_lang}, adapting idioms and expressions appropriately.
3. TONAL ALIGNMENT: Ensure the register strictly respects the requested tone ({tone}) (e.g., formal/informal address, technical jargon level).
4. NO LOSS OF MEANING: Do not alter the core message or structural layout of the draft text.

### INPUT DATA
- Target Language: {target_lang}
- Desired Tone: {tone}
- Source Text (Reference): {source_text}
- Draft Translation: {draft_translation}

### OUTPUT FORMAT
Return a valid JSON object with the following structure:
{{
  "corrected_text": "The fully polished and grammatically flawless translated text.",
  "edits_made": [
    {{
      "type": "Grammar | Fluency | Style",
      "original_phrase": "phrase from draft",
      "revised_phrase": "corrected phrase",
      "reason": "Brief explanation of the change"
    }}
  ]
}}
"""

GLOSSARY_SYSTEM = """\
You are the Terminology & Consistency Specialist in a multi-agent translation pipeline.

### CORE TASK
Enforce the strict application of the provided GLOSSARY and ensure terminology, key concepts, and formatting remain consistent throughout the text.

### CRITICAL RULES
1. GLOSSARY OVERRIDE: If a term in the source text matches an entry in the user glossary, its specified target translation MUST be used verbatim in the final text.
2. CONSISTENCY CHECK: Ensure named entities, product terms, technical words, and recurring phrases are translated identically across the entire text.
3. CONTEXT INTEGRATION: Ensure glossary terms fit naturally into the surrounding sentence syntax without breaking target language grammar.

### INPUT DATA
- Target Language: {target_lang}
- Current Revised Text: {revised_text}
- User Glossary (JSON mapping):
{glossary_json}

### OUTPUT FORMAT
Return a valid JSON object with the following structure:
{{
  "final_glossary_applied_text": "The text with all glossary terms accurately and naturally integrated.",
  "glossary_matches": [
    {{
      "source_term": "term in source",
      "forced_target_term": "term required by glossary",
      "status": "Applied | Already Present | Adapted for Grammar"
    }}
  ]
}}
"""

VALIDATOR_SYSTEM = """\
You are the Final Quality Assurance (QA) Arbitrator in a multi-agent translation pipeline.

### CORE TASK
Perform a final audit comparing the original SOURCE TEXT against the POLISHED TRANSLATION. Detect hallucinations, omitted content, or accidental shifts in original meaning introduced during earlier refinement steps.

### CRITICAL RULES
1. HALLUCINATION & OMISSION DETECTION: Compare line-by-line. Ensure every piece of information in the source exists in the translation, and no fabricated information was added.
2. FIDELITY AUDIT: Confirm that the refinement agents did not alter critical facts, figures, dates, or negation logic (e.g., turning "not allowed" into "allowed").
3. FINAL DECISION: If minor issues exist, fix them directly in the final output. If major corruption occurred, flag it.

### INPUT DATA
- Source Language: {source_lang}
- Target Language: {target_lang}
- Original Source Text: {source_text}
- Candidate Translation: {candidate_text}

### OUTPUT FORMAT
Return a valid JSON object with the following structure:
{{
  "status": "PASSED | PASSED_WITH_CORRECTIONS",
  "fidelity_score": 98,
  "final_text": "The final, verified, production-ready translation text.",
  "flags": [
    {{
      "severity": "Low | Medium | High",
      "issue": "Description of hallucination, omission, or logic drift caught",
      "resolution": "How it was corrected in final_text"
    }}
  ]
}}
"""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _llm_from_config(config: RunnableConfig | None) -> BaseChatModel:
    """Resolve the LLM injected by the worker via config['configurable']['llm'].

    Falls back to the default local Ollama model (privacy-first) when none is
    injected (e.g. when invoking the graph directly without a runnable config).
    """
    if config:
        configurable = config.get("configurable") or {}
        llm = configurable.get("llm")
        if llm is not None:
            return llm  # type: ignore[return-value]
    return _default_llm()


def _invoke(llm: BaseChatModel, system: str, user: str) -> str:
    """Invoke the LLM with a system + user message, return raw text content."""
    resp = llm.invoke([SystemMessage(system), HumanMessage(user)])
    return resp.content if isinstance(resp.content, str) else str(resp.content)


def _extract_json(raw: str) -> dict[str, Any]:
    """Parse a JSON object from an LLM response, tolerating ```json fences.

    Mirrors the jsonRepair strategy: direct parse -> strip code fences -> parse.
    """
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip ```json ... ``` or ``` ... ``` fences.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Agent returned invalid JSON: {exc}\n--- raw ---\n{raw}") from exc
    raise ValueError(f"Agent returned invalid JSON.\n--- raw ---\n{raw}")


# --------------------------------------------------------------------------- #
# LangGraph nodes
# --------------------------------------------------------------------------- #


def draft_translator_node(state: TranslationState, config: RunnableConfig) -> dict[str, Any]:
    """Agent 1 — Draft Translator. Output: raw translated text only (CDC)."""
    llm = _llm_from_config(config)
    prompt = TRANSLATOR_SYSTEM.format(
        source_lang=state["source_lang"],
        target_lang=state["target_lang"],
        tone=state.get("tone", "Professional"),
        source_text=state["source_text"],
    )
    draft = _invoke(llm, prompt, "Translate the text above. Output ONLY the translation.")
    log = f"[translator] draft produced ({len(draft)} chars)"
    return {
        "draft_translation": draft,
        "logs": state.get("logs", []) + [log],
    }


def proofreader_node(state: TranslationState, config: RunnableConfig) -> dict[str, Any]:
    """Agent 2 — Grammar & Style Editor. Output JSON {corrected_text, edits_made}."""
    llm = _json_llm(_llm_from_config(config))
    draft = state.get("draft_translation") or ""
    prompt = PROOFREADER_SYSTEM.format(
        source_lang=state["source_lang"],
        target_lang=state["target_lang"],
        tone=state.get("tone", "Professional"),
        source_text=state["source_text"],
        draft_translation=draft,
    )
    raw = _invoke(llm, prompt, "Return the JSON object described above.")
    parsed = ProofreadOutput.model_validate(_extract_json(raw))
    log = f"[proofreader] {len(parsed.edits_made)} edits applied"
    return {
        "corrected_text": parsed.corrected_text,
        "edits_made": [e.model_dump() for e in parsed.edits_made],
        "logs": state.get("logs", []) + [log],
    }


def glossary_node(state: TranslationState, config: RunnableConfig) -> dict[str, Any]:
    """Agent 3 — Context & Glossary Controller. Output JSON {final_text, matches}."""
    llm = _json_llm(_llm_from_config(config))
    revised = state.get("corrected_text") or state.get("draft_translation") or ""
    glossary = state.get("glossary") or {}
    prompt = GLOSSARY_SYSTEM.format(
        target_lang=state["target_lang"],
        revised_text=revised,
        glossary_json=json.dumps(glossary, ensure_ascii=False, indent=2),
    )
    raw = _invoke(llm, prompt, "Return the JSON object described above.")
    parsed = GlossaryOutput.model_validate(_extract_json(raw))
    log = f"[glossary] {len(parsed.glossary_matches)} glossary terms resolved"
    return {
        "glossary_applied_text": parsed.final_glossary_applied_text,
        "glossary_matches": [m.model_dump() for m in parsed.glossary_matches],
        "logs": state.get("logs", []) + [log],
    }


def validator_node(state: TranslationState, config: RunnableConfig) -> dict[str, Any]:
    """Agent 4 — Validator & Arbitrator. Output JSON {status, score, final_text, flags}.

    Unlike the previous TS app (which DISCARDED this output), the validator's
    final_text becomes the pipeline result and its flags/score feed the UI
    inspector (CDC integration tip).
    """
    llm = _json_llm(_llm_from_config(config))
    candidate = (
        state.get("glossary_applied_text")
        or state.get("corrected_text")
        or state.get("draft_translation")
        or ""
    )
    prompt = VALIDATOR_SYSTEM.format(
        source_lang=state["source_lang"],
        target_lang=state["target_lang"],
        source_text=state["source_text"],
        candidate_text=candidate,
    )
    raw = _invoke(llm, prompt, "Return the JSON object described above.")
    parsed = ValidatorOutput.model_validate(_extract_json(raw))
    log = f"[validator] {parsed.status} (fidelity={parsed.fidelity_score}, {len(parsed.flags)} flags)"
    return {
        "final_text": parsed.final_text,
        "fidelity_score": parsed.fidelity_score,
        "status": parsed.status,
        "flags": [f.model_dump() for f in parsed.flags],
        "logs": state.get("logs", []) + [log],
    }


# --------------------------------------------------------------------------- #
# LLM resolution helpers
# --------------------------------------------------------------------------- #
#
# The active LLM is injected via set_llm() by the worker (from user config) or
# by tests. We deliberately do NOT rely on the LangGraph runnable config to
# carry it, because LangGraph strips/ignores custom config keys for nodes that
# do not strictly follow its RunnableConfig contract. A module-level holder is
# simple and reliable.

_active_llm: BaseChatModel | None = None


def set_llm(llm: BaseChatModel | None) -> None:
    """Inject the LLM the pipeline should use (called by the worker / tests)."""
    global _active_llm
    _active_llm = llm


def get_active_llm() -> BaseChatModel:
    """Return the injected LLM, or lazily build the default local Ollama one."""
    global _active_llm
    if _active_llm is not None:
        return _active_llm
    from src.core.llm import get_llm

    _active_llm = get_llm(provider="ollama", model="qwen2.5:7b")
    return _active_llm


def _llm_from_config(config: RunnableConfig | None) -> BaseChatModel:
    """Resolve the LLM. Reads the injected active LLM (ignores config).

    Kept for node signature compatibility with LangGraph.
    """
    return get_active_llm()


def _default_llm() -> BaseChatModel:
    """Backward-compatible alias for get_active_llm()."""
    return get_active_llm()


def _json_llm(llm: BaseChatModel | None) -> BaseChatModel:
    """Return a JSON-mode-bound view of the LLM if the provider supports it.

    Ollama supports format='json'; OpenAI supports response_format json_object.
    We attempt binding and fall back to the raw LLM on failure.
    """
    if llm is None:
        llm = _default_llm()
    try:
        return llm.bind(response_format={"type": "json_object"})  # type: ignore[attr-defined]
    except Exception:
        return llm

"""Pydantic models for agents 2/3/4 JSON outputs.

Field names are EXACTLY the ones mandated by the CDC (§3 prompts):
  - ProofreadOutput:  { corrected_text, edits_made[] }
  - GlossaryOutput:   { final_glossary_applied_text, glossary_matches[] }
  - ValidatorOutput:  { status, fidelity_score, final_text, flags[] }

This is what the previous TS implementation failed to do (CDC_GAP_ANALYSIS.md §2):
here the CDC schemas are the contract, validated by Pydantic at parse time.

Robustness: local LLMs (qwen2.5:7b etc.) do not always honor strict enums —
e.g. they may return "Already Present | Not Applicable" for a glossary status.
The _coerce_enum validator normalizes such values to the closest valid option
so the pipeline does not crash on minor prompt drift.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _coerce_enum(value: str, allowed: tuple[str, ...], default: str) -> str:
    """Normalize an LLM-emitted enum value to one of the allowed options.

    Strategy: exact match -> prefix match -> first token match -> default.
    """
    if not isinstance(value, str):
        return default
    v = value.strip()
    if v in allowed:
        return v
    low = v.lower()
    # Try longest option first so "PASSED_WITH_CORRECTIONS" wins over "PASSED".
    for opt in sorted(allowed, key=len, reverse=True):
        if low.startswith(opt.lower()) or opt.lower() in low:
            return opt
    # Fall back to the first token (e.g. "Applied | ..." -> "Applied").
    first = v.split("|")[0].split("/")[0].strip()
    if first in allowed:
        return first
    return default


class Edit(BaseModel):
    """One revision produced by the Grammar & Style agent."""

    type: Literal["Grammar", "Fluency", "Style"] = "Style"
    original_phrase: str = ""
    revised_phrase: str = ""
    reason: str = ""

    @field_validator("type", mode="before")
    @classmethod
    def _norm_type(cls, v):
        return _coerce_enum(v, ("Grammar", "Fluency", "Style"), "Style")


class ProofreadOutput(BaseModel):
    """Agent 2 — Grammar & Style Editor output (CDC §3)."""

    corrected_text: str
    edits_made: list[Edit] = Field(default_factory=list)


class GlossaryMatch(BaseModel):
    """One glossary term resolution produced by the Context & Glossary agent."""

    source_term: str = ""
    forced_target_term: str = ""
    status: Literal["Applied", "Already Present", "Adapted for Grammar"] = "Applied"

    @field_validator("status", mode="before")
    @classmethod
    def _norm_status(cls, v):
        return _coerce_enum(
            v, ("Applied", "Already Present", "Adapted for Grammar"), "Applied"
        )


class GlossaryOutput(BaseModel):
    """Agent 3 — Context & Glossary Controller output (CDC §3)."""

    final_glossary_applied_text: str
    glossary_matches: list[GlossaryMatch] = Field(default_factory=list)


class Flag(BaseModel):
    """One QA issue caught by the Validator."""

    severity: Literal["Low", "Medium", "High"] = "Low"
    issue: str = ""
    resolution: str = ""

    @field_validator("severity", mode="before")
    @classmethod
    def _norm_severity(cls, v):
        return _coerce_enum(v, ("Low", "Medium", "High"), "Low")


class ValidatorOutput(BaseModel):
    """Agent 4 — Validator & Arbitrator output (CDC §3)."""

    status: Literal["PASSED", "PASSED_WITH_CORRECTIONS"] = "PASSED"
    fidelity_score: int = Field(ge=0, le=100)
    final_text: str
    flags: list[Flag] = Field(default_factory=list)

    @field_validator("status", mode="before")
    @classmethod
    def _norm_validator_status(cls, v):
        return _coerce_enum(
            v,
            ("PASSED", "PASSED_WITH_CORRECTIONS"),
            "PASSED",
        )

    @field_validator("fidelity_score", mode="before")
    @classmethod
    def _clamp_score(cls, v):
        """Coerce out-of-range scores to the valid bounds (LLMs may return 101 or -1)."""
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 50
        return max(0, min(100, n))

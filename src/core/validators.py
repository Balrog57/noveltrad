"""Pydantic models for agents 2/3/4 JSON outputs.

Field names are EXACTLY the ones mandated by the CDC (§3 prompts):
  - ProofreadOutput:  { corrected_text, edits_made[] }
  - GlossaryOutput:   { final_glossary_applied_text, glossary_matches[] }
  - ValidatorOutput:  { status, fidelity_score, final_text, flags[] }

This is what the previous TS implementation failed to do (CDC_GAP_ANALYSIS.md §2):
here the CDC schemas are the contract, validated by Pydantic at parse time.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Edit(BaseModel):
    """One revision produced by the Grammar & Style agent."""

    type: Literal["Grammar", "Fluency", "Style"] = "Style"
    original_phrase: str
    revised_phrase: str
    reason: str


class ProofreadOutput(BaseModel):
    """Agent 2 — Grammar & Style Editor output (CDC §3)."""

    corrected_text: str
    edits_made: list[Edit] = Field(default_factory=list)


class GlossaryMatch(BaseModel):
    """One glossary term resolution produced by the Context & Glossary agent."""

    source_term: str
    forced_target_term: str
    status: Literal["Applied", "Already Present", "Adapted for Grammar"] = "Applied"


class GlossaryOutput(BaseModel):
    """Agent 3 — Context & Glossary Controller output (CDC §3)."""

    final_glossary_applied_text: str
    glossary_matches: list[GlossaryMatch] = Field(default_factory=list)


class Flag(BaseModel):
    """One QA issue caught by the Validator."""

    severity: Literal["Low", "Medium", "High"] = "Low"
    issue: str
    resolution: str = ""


class ValidatorOutput(BaseModel):
    """Agent 4 — Validator & Arbitrator output (CDC §3)."""

    status: Literal["PASSED", "PASSED_WITH_CORRECTIONS"] = "PASSED"
    fidelity_score: int = Field(ge=0, le=100)
    final_text: str
    flags: list[Flag] = Field(default_factory=list)

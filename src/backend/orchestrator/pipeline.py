"""Pipeline topology — directed graph of agent stages.

Defines the canonical 9-agent flow from the v4 plan:

    Parser -> FastTranslator -> LexiconBuilder -> GlossaryApplier
           -> ConsistencyChecker -> QAValidator -> GrammarProofer
           -> LLMPolisher -> Assembler

Plus:
  - the channels (queues) that connect stages
  - a "stage_key" -> (input_queue, output_queue, agent_module) registry
  - helpers to wire a fresh topology and to inspect it

This module is PURE DATA. It does not spawn processes or touch the State
Store. Worker lifecycle lives in worker_manager.py; runtime coordination
lives in orchestrator.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


# Stage identifiers (also used as worker_id prefixes).
PARSER = "parser"
FAST_TRANSLATOR = "fast_translator"
LEXICON_BUILDER = "lexicon_builder"
GLOSSARY_APPLIER = "glossary_applier"
CONSISTENCY_CHECKER = "consistency_checker"
QA_VALIDATOR = "qa_validator"
GRAMMAR_PROOFER = "grammar_proofer"
LLM_POLISHER = "llm_polisher"
ASSEMBLER = "assembler"


ALL_STAGES: tuple[str, ...] = (
    PARSER,
    FAST_TRANSLATOR,
    LEXICON_BUILDER,
    GLOSSARY_APPLIER,
    CONSISTENCY_CHECKER,
    QA_VALIDATOR,
    GRAMMAR_PROOFER,
    LLM_POLISHER,
    ASSEMBLER,
)


# Default ordering for the pipeline run.
DEFAULT_PIPELINE_ORDER: tuple[str, ...] = (
    PARSER,
    FAST_TRANSLATOR,
    LEXICON_BUILDER,
    GLOSSARY_APPLIER,
    CONSISTENCY_CHECKER,
    QA_VALIDATOR,
    GRAMMAR_PROOFER,
    LLM_POLISHER,
    ASSEMBLER,
)


# Stages that are safe to run with >1 worker concurrently.
# FastTranslator and LLMPolisher are parallelizable per the plan.
PARALLELIZABLE_STAGES: frozenset[str] = frozenset(
    {FAST_TRANSLATOR, LLM_POLISHER, CONSISTENCY_CHECKER}
)


@dataclass(frozen=True)
class Channel:
    """A message channel between two stages."""

    name: str
    source: str  # stage_key that produces messages
    target: str  # stage_key that consumes messages


@dataclass(frozen=True)
class StageSpec:
    """Static description of one pipeline stage."""

    key: str
    agent_module: str  # dotted import path, e.g. "src.backend.agents.parser"
    input_channel: str
    output_channel: str
    parallelizable: bool = False
    extra_options: dict[str, object] = field(default_factory=dict)


def build_channels() -> tuple[Channel, ...]:
    """Return the linear channel sequence used by DEFAULT_PIPELINE_ORDER."""
    pairs = list(zip(DEFAULT_PIPELINE_ORDER, DEFAULT_PIPELINE_ORDER[1:]))
    return tuple(
        Channel(
            name=f"{src}__to__{tgt}",
            source=src,
            target=tgt,
        )
        for src, tgt in pairs
    )


# The special "control" channel used by the orchestrator to dispatch
# non-chunk events (shutdown, pause, reprocess). All workers listen.
CONTROL_CHANNEL = "control"


def build_stages() -> dict[str, StageSpec]:
    """Return the canonical stage registry.

    Channel naming uses the "X__to__Y" convention; each stage reads from
    its `input_channel` and writes to its `output_channel`. The first
    stage (Parser) is fed directly by the orchestrator — its input
    channel is the synthetic "parser_in" feed. The last stage (Assembler)
    writes its results back to the orchestrator via the special
    "assembler_out" channel.
    """
    channels = {c.name: c for c in build_channels()}
    # Synthetic feeds
    channels["parser_in"] = Channel(
        name="parser_in", source="orchestrator", target=PARSER
    )
    channels["assembler_out"] = Channel(
        name="assembler_out", source=ASSEMBLER, target="orchestrator"
    )

    return {
        PARSER: StageSpec(
            key=PARSER,
            agent_module="src.backend.agents.parser",
            input_channel="parser_in",
            output_channel=f"{PARSER}__to__{FAST_TRANSLATOR}",
        ),
        FAST_TRANSLATOR: StageSpec(
            key=FAST_TRANSLATOR,
            agent_module="src.backend.agents.fast_translator",
            input_channel=f"{PARSER}__to__{FAST_TRANSLATOR}",
            output_channel=f"{FAST_TRANSLATOR}__to__{LEXICON_BUILDER}",
            parallelizable=True,
        ),
        LEXICON_BUILDER: StageSpec(
            key=LEXICON_BUILDER,
            agent_module="src.backend.agents.lexicon_builder",
            input_channel=f"{FAST_TRANSLATOR}__to__{LEXICON_BUILDER}",
            output_channel=f"{LEXICON_BUILDER}__to__{GLOSSARY_APPLIER}",
            extra_options={"emits_lexicon_ready": True},
        ),
        GLOSSARY_APPLIER: StageSpec(
            key=GLOSSARY_APPLIER,
            agent_module="src.backend.agents.glossary_applier",
            input_channel=f"{LEXICON_BUILDER}__to__{GLOSSARY_APPLIER}",
            output_channel=f"{GLOSSARY_APPLIER}__to__{CONSISTENCY_CHECKER}",
        ),
        CONSISTENCY_CHECKER: StageSpec(
            key=CONSISTENCY_CHECKER,
            agent_module="src.backend.agents.consistency_checker",
            input_channel=f"{GLOSSARY_APPLIER}__to__{CONSISTENCY_CHECKER}",
            output_channel=f"{CONSISTENCY_CHECKER}__to__{QA_VALIDATOR}",
            parallelizable=True,
        ),
        QA_VALIDATOR: StageSpec(
            key=QA_VALIDATOR,
            agent_module="src.backend.agents.qa_validator",
            input_channel=f"{CONSISTENCY_CHECKER}__to__{QA_VALIDATOR}",
            output_channel=f"{QA_VALIDATOR}__to__{GRAMMAR_PROOFER}",
        ),
        GRAMMAR_PROOFER: StageSpec(
            key=GRAMMAR_PROOFER,
            agent_module="src.backend.agents.grammar_proofer",
            input_channel=f"{QA_VALIDATOR}__to__{GRAMMAR_PROOFER}",
            output_channel=f"{GRAMMAR_PROOFER}__to__{LLM_POLISHER}",
        ),
        LLM_POLISHER: StageSpec(
            key=LLM_POLISHER,
            agent_module="src.backend.agents.llm_polisher",
            input_channel=f"{GRAMMAR_PROOFER}__to__{LLM_POLISHER}",
            output_channel=f"{LLM_POLISHER}__to__{ASSEMBLER}",
            parallelizable=True,
        ),
        ASSEMBLER: StageSpec(
            key=ASSEMBLER,
            agent_module="src.backend.agents.assembler",
            input_channel=f"{LLM_POLISHER}__to__{ASSEMBLER}",
            output_channel="assembler_out",
        ),
    }


# Status strings used on chunks.status and emitted in messages.
# Mirrors the SQLite CHECK-style list in the plan.
STATUS_PARSED = "parsed"
STATUS_FAST_TRANSLATED = "fast_translated"
STATUS_GLOSSARY_APPLIED = "glossary_applied"
STATUS_CONSISTENCY_CHECKED = "consistency_checked"
STATUS_QA_CHECKED = "qa_checked"
STATUS_GRAMMAR_CHECKED = "grammar_checked"
STATUS_POLISHED = "polished"
STATUS_ASSEMBLED = "assembled"
STATUS_WAITING_FOR_HUMAN = "waiting_for_human"
STATUS_ERROR = "error"


# Map: stage -> chunk status the stage produces on success.
STAGE_TO_STATUS: dict[str, str] = {
    PARSER: STATUS_PARSED,
    FAST_TRANSLATOR: STATUS_FAST_TRANSLATED,
    GLOSSARY_APPLIER: STATUS_GLOSSARY_APPLIED,
    CONSISTENCY_CHECKER: STATUS_CONSISTENCY_CHECKED,
    QA_VALIDATOR: STATUS_QA_CHECKED,
    GRAMMAR_PROOFER: STATUS_GRAMMAR_CHECKED,
    LLM_POLISHER: STATUS_POLISHED,
    ASSEMBLER: STATUS_ASSEMBLED,
}


def iter_stages(order: Iterable[str] | None = None) -> Iterable[StageSpec]:
    """Yield StageSpec objects in the given order (default = canonical)."""
    registry = build_stages()
    for key in (order or DEFAULT_PIPELINE_ORDER):
        if key not in registry:
            raise KeyError(f"Unknown stage: {key}")
        yield registry[key]

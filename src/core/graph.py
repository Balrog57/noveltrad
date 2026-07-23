"""LangGraph StateGraph construction.

CDC §3 pipeline (4 agents):
    translator -> proofreader -> glossary -> validator -> END

The CDC's sample graph.py only wired 3 nodes (translator/proofreader/validator),
but the pipeline diagram in §3 clearly describes 4 stages. We implement the
complete 4-agent graph, inserting the glossary node between proofreader and
validator as described in the prose.

The graph is compiled WITHOUT checkpointer (in-memory, one-shot translation of
the current selection). LangGraph merges each node's returned dict into state.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.core.agents import (
    draft_translator_node,
    glossary_node,
    proofreader_node,
    validator_node,
)
from src.core.state import TranslationState


def build_translation_graph():
    """Compile and return the 4-agent translation StateGraph."""
    workflow = StateGraph(TranslationState)

    # 4 agent nodes (CDC §3).
    workflow.add_node("translator", draft_translator_node)
    workflow.add_node("proofreader", proofreader_node)
    workflow.add_node("glossary", glossary_node)
    workflow.add_node("validator", validator_node)

    # Sequential edges.
    workflow.add_edge(START, "translator")
    workflow.add_edge("translator", "proofreader")
    workflow.add_edge("proofreader", "glossary")
    workflow.add_edge("glossary", "validator")
    workflow.add_edge("validator", END)

    return workflow.compile()


def build_fast_graph():
    """CDC §5 'Mode Rapide' — single-agent pipeline (translator only).

    Falls back to a single translation pass without proofreading/glossary/QA,
    for when speed matters more than quality (< 3s target).
    """
    workflow = StateGraph(TranslationState)
    workflow.add_node("translator", draft_translator_node)
    workflow.add_edge(START, "translator")
    workflow.add_edge("translator", END)
    return workflow.compile()

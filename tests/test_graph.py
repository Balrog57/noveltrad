"""End-to-end pipeline tests (CDC §3 graph).

Runs the full 4-agent graph and the fast (1-agent) graph with a fake LLM and
asserts the CDC contract:
  - final_text is produced,
  - logs accumulate one entry per agent,
  - stream() emits one event per node.
"""

from __future__ import annotations

import json

from src.core.graph import build_fast_graph, build_translation_graph
from src.core.state import make_initial_state


def _config():
    return {"recursion_limit": 25}


def _expert_responses():
    """One canned CDC-shaped response per agent, in pipeline order."""
    return [
        # translator -> raw text
        "Bonjour le monde.",
        # proofreader -> JSON
        json.dumps({"corrected_text": "Bonjour le monde.", "edits_made": []}),
        # glossary -> JSON
        json.dumps({"final_glossary_applied_text": "Bonjour le monde.",
                    "glossary_matches": []}),
        # validator -> JSON
        json.dumps({"status": "PASSED", "fidelity_score": 96,
                    "final_text": "Bonjour le monde.", "flags": []}),
    ]


def test_expert_graph_invoke_produces_final_text(fake_llm_factory) -> None:
    fake_llm_factory(_expert_responses())
    graph = build_translation_graph()
    state = make_initial_state("Hello world.", "Anglais", "Français")
    result = graph.invoke(state, config=_config())

    assert result["final_text"] == "Bonjour le monde."
    assert result["fidelity_score"] == 96
    assert result["status"] == "PASSED"
    # Intermediate stages populated.
    assert result["draft_translation"] == "Bonjour le monde."
    assert result["corrected_text"] == "Bonjour le monde."
    assert result["glossary_applied_text"] == "Bonjour le monde."


def test_expert_graph_logs_accumulate_per_agent(fake_llm_factory) -> None:
    fake_llm_factory(_expert_responses())
    graph = build_translation_graph()
    state = make_initial_state("Hello world.", "Anglais", "Français")
    result = graph.invoke(state, config=_config())

    logs = result["logs"]
    assert len(logs) == 4
    assert "[translator]" in logs[0]
    assert "[proofreader]" in logs[1]
    assert "[glossary]" in logs[2]
    assert "[validator]" in logs[3]


def test_expert_graph_stream_emits_one_event_per_node(fake_llm_factory) -> None:
    fake_llm_factory(_expert_responses())
    graph = build_translation_graph()
    state = make_initial_state("Hello world.", "Anglais", "Français")

    events = list(graph.stream(state, config=_config()))
    node_names = [next(iter(e)) for e in events]
    assert node_names == ["translator", "proofreader", "glossary", "validator"]


def test_fast_graph_single_agent(fake_llm_factory) -> None:
    fake_llm_factory(["Bonjour."])
    graph = build_fast_graph()
    state = make_initial_state("Hello.", "Anglais", "Français")
    result = graph.invoke(state, config=_config())

    # Fast mode: only the translator runs; final_text falls back to draft.
    assert result["draft_translation"] == "Bonjour."
    assert result.get("final_text") in (None, "Bonjour.")
    # No proofreader/glossary/validator logs.
    assert len(result["logs"]) == 1

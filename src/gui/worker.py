"""QThread worker that runs the LangGraph pipeline off the UI thread.

CDC §4 (src/gui/worker.py). The graph.stream() loop lets the UI update the
inspector panel in real time as each agent completes.

Signals:
  - step_completed(node_name, log_msg)  : one per agent node finishing
  - stage_output(stage, payload_dict)   : the parsed JSON output of agents 2/3/4
                                          (feeds the diff-viewer / inspector)
  - translation_finished(final_state)   : full state dict at the end
  - error_occurred(err_msg)
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QThread, Signal

from src.core.agents import set_llm
from src.core.graph import build_fast_graph, build_translation_graph
from src.core.llm import get_llm
from src.core.state import TranslationState
from src.utils.config import Config


class TranslationWorker(QThread):
    step_completed = Signal(str, str)  # (node_name, log_msg)
    stage_output = Signal(str, dict)  # (stage, payload) — for the inspector
    translation_finished = Signal(dict)  # final state
    error_occurred = Signal(str)

    def __init__(self, initial_state: TranslationState, config: Config) -> None:
        super().__init__()
        self.state = initial_state
        self.config = config
        expert = config.get("expert_mode", True)
        self.graph = build_translation_graph() if expert else build_fast_graph()

    def run(self) -> None:  # noqa: C901 - straightforward stream loop
        try:
            # Build the LLM from user config and inject it for the pipeline nodes.
            llm = get_llm(
                provider=self.config.get("provider", "ollama"),
                model=self.config.get("model", "qwen2.5:7b"),
                base_url=(
                    self.config.get("ollama_host")
                    if self.config.get("provider", "ollama") == "ollama"
                    else self.config.get("remote_base_url") or None
                ),
                api_key=self.config.get("api_key") or None,
            )
            set_llm(llm)

            final_state: dict[str, Any] = dict(self.state)
            # Mode streaming de LangGraph pour capter la fin de chaque agent.
            for event in self.graph.stream(self.state, config={"recursion_limit": 25}):
                # Each event is {node_name: {updated_state_keys...}}
                for node_name, node_output in event.items():
                    if not isinstance(node_output, dict):
                        continue
                    final_state.update(node_output)
                    logs = node_output.get("logs") or []
                    log_msg = logs[-1] if logs else f"Agent {node_name} terminé."
                    self.step_completed.emit(node_name, log_msg)
                    self._emit_stage_output(node_name, node_output)

            self.translation_finished.emit(final_state)
        except Exception as exc:  # noqa: BLE001 - surface any error to the UI
            self.error_occurred.emit(str(exc))

    def _emit_stage_output(self, node_name: str, node_output: dict[str, Any]) -> None:
        """Forward the structured payload of agents 2/3/4 to the inspector."""
        stage_map = {
            "proofreader": ("corrected_text", "edits_made"),
            "glossary": ("glossary_applied_text", "glossary_matches"),
            "validator": ("final_text", "flags"),
        }
        if node_name in stage_map:
            text_key, list_key = stage_map[node_name]
            payload = {
                "text": node_output.get(text_key),
                "items": node_output.get(list_key) or [],
            }
            # Validator also carries the score & status.
            if node_name == "validator":
                payload["fidelity_score"] = node_output.get("fidelity_score")
                payload["status"] = node_output.get("status")
            self.stage_output.emit(node_name, payload)

"""One-pass refinement checkpoint helpers.

Handlers resume refine jobs via ``load_refinement_state``. The three-pass
wrappers used to persist that file; the one-pass path must do the same.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _call_with_optional_scope(method, translation_id: str, *args, scope: str = "global"):
    """Support both CheckpointManager (scope kw) and simple test doubles."""
    try:
        return method(translation_id, *args, scope=scope)
    except TypeError:
        return method(translation_id, *args)


def load_one_pass_state(
    checkpoint_manager,
    translation_id: Optional[str],
    *,
    total_segments: int,
    scope: str = "global",
) -> Tuple[int, Optional[Any], Optional[Dict[str, Any]]]:
    """Return ``(start_index, current, raw_state)``. Start at 0 if none/invalid."""
    if not checkpoint_manager or not translation_id:
        return 0, None, None
    try:
        state = _call_with_optional_scope(
            checkpoint_manager.load_refinement_state, translation_id, scope=scope
        )
    except Exception:
        return 0, None, None
    if not isinstance(state, dict) or state.get("version") != 1:
        return 0, None, None

    current = state.get("current")
    try:
        next_segment = int(state.get("next_segment") or 0)
    except (TypeError, ValueError):
        next_segment = 0
    if next_segment < 0:
        next_segment = 0

    if isinstance(current, list) and len(current) == total_segments:
        return min(next_segment, total_segments), current, state
    if isinstance(current, dict):
        return next_segment, current, state
    if state.get("total_segments") == total_segments:
        return min(next_segment, total_segments), current, state
    return 0, None, state


def save_one_pass_state(
    checkpoint_manager,
    translation_id: Optional[str],
    *,
    next_segment: int,
    total_segments: int,
    current: Any,
    output_filepath: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    scope: str = "global",
    log_callback=None,
) -> Optional[Dict[str, Any]]:
    """Persist one-pass refine progress. Returns the state dict even if I/O fails."""
    if not checkpoint_manager or not translation_id:
        return None
    state: Dict[str, Any] = {
        "version": 1,
        "phase": 1,
        "next_segment": next_segment,
        "total_segments": total_segments,
        "current": current,
    }
    if output_filepath:
        state["output_filepath"] = output_filepath
    if extra:
        for key, value in extra.items():
            if value is not None:
                state[key] = value
    try:
        _call_with_optional_scope(
            checkpoint_manager.save_refinement_state,
            translation_id,
            state,
            scope=scope,
        )
    except Exception:
        if log_callback:
            log_callback(
                "refinement_checkpoint_warning",
                "⚠️ Could not persist refinement checkpoint.",
            )
    return state


def clear_one_pass_state(
    checkpoint_manager,
    translation_id: Optional[str],
    *,
    scope: str = "global",
) -> None:
    if not checkpoint_manager or not translation_id:
        return
    try:
        _call_with_optional_scope(
            checkpoint_manager.delete_refinement_state, translation_id, scope=scope
        )
    except Exception:
        pass

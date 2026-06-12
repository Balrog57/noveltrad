"""Shared dependencies for route modules.

``Deps`` is a small container that the app factory builds once and
passes to every ``register(app, deps)`` call. It avoids the
``app.state`` magic-attribute pattern and makes the route modules
trivial to unit-test by constructing a fake ``Deps`` instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.orchestrator.orchestrator import Orchestrator
    from src.backend.orchestrator.state_store import StateStore


@dataclass
class Deps:
    store: "StateStore"
    orchestrator: "Orchestrator"


__all__ = ["Deps"]

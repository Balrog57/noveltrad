"""HTTP route modules for the NovelTrad backend.

Each module exposes a single ``register(app, deps) -> None`` function
that the app factory calls in turn. ``Deps`` is a small container
holding the shared ``StateStore`` and ``Orchestrator``; see
``deps.py``. Pydantic models live in ``schemas.py`` and are built
lazily by ``build_schemas()`` so a missing ``pydantic`` import does
not break module loading.
"""

from __future__ import annotations

from .deps import Deps
from .schemas import build_schemas

__all__ = ["Deps", "build_schemas"]

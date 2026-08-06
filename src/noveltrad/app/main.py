"""Streamlit entry point (SDD 20.12 app/main.py).

Thin bootstrap: builds the container and delegates to the UI router.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from noveltrad.app.container import Container  # noqa: E402

_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def run() -> None:
    from noveltrad.ui.router import Router

    container = get_container()
    router = Router(container)
    router.render()


run()

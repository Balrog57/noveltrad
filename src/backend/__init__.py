"""NovelTrad v4 backend package.

FastAPI server hosting the multi-agent translation orchestrator.

Import-order note (see AGENTS.md): onnxruntime/ctranslate2 MUST be imported
before PyQt6 to avoid Windows DLL conflicts (msvcp140, zlib). The backend
itself is GUI-free, so this concern mostly matters for the entrypoint
that bridges backend+GUI (src/main_qt.py).
"""

from src import __version__  # noqa: F401  — single version source of truth

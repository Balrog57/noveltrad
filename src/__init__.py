"""NovelTrad v4 — top-level package.

Single source of truth for the application version. The build script
and the GUI auto-updater both import ``src.__version__`` so the wheel,
the PyInstaller bundle, and the Inno Setup installer all agree.
"""

from __future__ import annotations

__version__ = "4.1.0"

__all__ = ["__version__"]

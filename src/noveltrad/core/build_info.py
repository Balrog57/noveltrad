"""Build information incorporated into the image (SDD 6.11).

`__version__` mirrors pyproject.toml. `SOURCE_COMMIT` is injected by the
Docker build via the SOURCE_COMMIT argument; locally it falls back to the
current git HEAD when available, otherwise to an empty marker.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

__version__ = "0.1.0"

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _git_head() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


_source_commit = ""

try:  # pragma: no cover - injected at image build time
    import noveltrad.core._build_env as _build_env

    _source_commit = _build_env.SOURCE_COMMIT  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - fallback path
    _source_commit = _git_head()


def source_commit() -> str:
    """Return the incorporated SOURCE_COMMIT, or the git HEAD fallback."""
    return _source_commit

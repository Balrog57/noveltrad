"""Confined relative paths (SDD 8.12, 10.6, 8.13).

All paths stored in SQLite are relative to the project directory. This
module guarantees any resolved path stays under one of the exact roots:
data/tmp, data/trash, data/backups or the project directories.
"""

from __future__ import annotations

import posixpath
from pathlib import Path

from .exceptions import ValidationError

_TMP = "tmp"
_TRASH = "trash"
_BACKUPS = "backups"
_PROJECTS = "projects"

_ALLOWED_ROOTS = (_TMP, _TRASH, _BACKUPS, _PROJECTS)


def normalize_relative(path: str) -> str:
    """Validate and normalize a stored relative path (POSIX style)."""
    if not path or "\x00" in path or "\\" in path:
        raise ValidationError("invalid stored path")
    normalized = posixpath.normpath(path)
    if normalized.startswith(("..", "/")):
        raise ValidationError("stored path escapes its root")
    return normalized


def project_dir(data_dir: Path, project_id: int) -> Path:
    return data_dir / _PROJECTS / str(project_id)


def document_dir(data_dir: Path, project_id: int, document_id: int) -> Path:
    return project_dir(data_dir, project_id) / str(document_id)


def tmp_dir(data_dir: Path) -> Path:
    return data_dir / _TMP


def trash_dir(data_dir: Path) -> Path:
    return data_dir / _TRASH


def backups_dir(data_dir: Path) -> Path:
    return data_dir / _BACKUPS


def resolve(data_dir: Path, relative: str) -> Path:
    """Resolve a stored relative path under the data root, confined."""
    normalized = normalize_relative(relative)
    root = normalized.split("/", 1)[0]
    if root not in _ALLOWED_ROOTS:
        raise ValidationError(f"stored path outside allowed roots: {normalized}")
    resolved = (data_dir / normalized).resolve()
    base = data_dir.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValidationError("stored path escapes the data directory") from exc
    return resolved

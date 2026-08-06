"""Atomic file writes with fsync and atomic replace (SDD 16.4, 8.13).

Writes are written to a temporary file in the same directory, fsync'ed,
atomically renamed over the target, then the parent directory is
synchronized when the platform supports it. Any translated.md write is
atomic.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from .exceptions import StorageError

_BLOCK = 1024 * 1024


def _fsync_dir(directory: Path) -> None:
    """Best-effort directory sync; not supported on Windows."""
    if os.name == "nt":
        return
    try:
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def write_atomic(target: Path, content: bytes, fsync: bool = True) -> None:
    """Atomically write ``content`` to ``target``."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            if fsync:
                handle.flush()
                os.fsync(handle.fileno())
        os.replace(tmp_name, target)
        if fsync:
            _fsync_dir(target.parent)
    except OSError as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise StorageError(f"atomic write failed for {target.name}: {exc}") from exc


def copy_atomic(source: Path, target: Path, fsync: bool = True) -> None:
    """Atomically copy ``source`` to ``target`` (bounded streaming)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as inp:
            while True:
                chunk = inp.read(_BLOCK)
                if not chunk:
                    break
                out.write(chunk)
            if fsync:
                out.flush()
                os.fsync(out.fileno())
        os.replace(tmp_name, target)
        if fsync:
            _fsync_dir(target.parent)
    except OSError as exc:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise StorageError(f"atomic copy failed for {target.name}: {exc}") from exc


def rename_atomic(source: Path, target: Path, fsync: bool = True) -> None:
    """Atomically move ``source`` to ``target`` across the same filesystem."""
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(source, target)
        if fsync:
            _fsync_dir(target.parent)
    except OSError as exc:
        raise StorageError(f"atomic rename failed: {exc}") from exc


def ensure_free_space(path: Path, required_bytes: int) -> None:
    """Fail when the filesystem hosting ``path`` has insufficient free space."""
    try:
        import shutil

        free = shutil.disk_usage(path).free
    except OSError as exc:
        raise StorageError(f"cannot stat disk usage: {exc}") from exc
    if free < required_bytes:
        raise StorageError(f"insufficient disk space: {free} bytes free, {required_bytes} required")

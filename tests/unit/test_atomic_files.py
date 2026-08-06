"""Unit tests for core.atomic_files (SDD 16.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from noveltrad.core.atomic_files import copy_atomic, rename_atomic, write_atomic
from noveltrad.core.exceptions import StorageError


def test_write_atomic_creates_file(tmp_path: Path):
    target = tmp_path / "out.md"
    write_atomic(target, b"hello")
    assert target.read_bytes() == b"hello"


def test_write_atomic_replaces(tmp_path: Path):
    target = tmp_path / "out.md"
    write_atomic(target, b"one")
    write_atomic(target, b"two")
    assert target.read_bytes() == b"two"


def test_copy_atomic(tmp_path: Path):
    source = tmp_path / "a.bin"
    source.write_bytes(b"\x00" * 3000000)
    target = tmp_path / "b.bin"
    copy_atomic(source, target)
    assert target.read_bytes() == source.read_bytes()


def test_rename_atomic(tmp_path: Path):
    source = tmp_path / "a.txt"
    source.write_text("x")
    target = tmp_path / "b.txt"
    rename_atomic(source, target)
    assert target.exists()
    assert not source.exists()


def test_copy_missing_source_fails(tmp_path: Path):
    with pytest.raises(StorageError):
        copy_atomic(tmp_path / "missing", tmp_path / "out")

"""Unit tests for core.paths (SDD 8.12, 10.6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from noveltrad.core.exceptions import ValidationError
from noveltrad.core.paths import (
    document_dir,
    normalize_relative,
    project_dir,
    resolve,
    tmp_dir,
    trash_dir,
)


def test_normalize_relative_rejects_escape():
    for bad in ("", "../x", "/abs", "a\\b", "a\x00b"):
        with pytest.raises(ValidationError):
            normalize_relative(bad)


def test_normalize_relative_accepts():
    assert normalize_relative("projects/1/2/source.md") == "projects/1/2/source.md"
    assert normalize_relative("a/../b.md") == "b.md"


def test_resolve_confines_to_data(tmp_path: Path):
    base = tmp_path / "data"
    base.mkdir()
    resolved = resolve(base, "tmp/import-1/lot.md")
    assert resolved == (base / "tmp" / "import-1" / "lot.md").resolve()


def test_resolve_rejects_outside_roots(tmp_path: Path):
    base = tmp_path / "data"
    base.mkdir()
    with pytest.raises(ValidationError):
        resolve(base, "etc/passwd")


def test_dir_helpers(tmp_path: Path):
    base = tmp_path / "data"
    assert project_dir(base, 3) == base / "projects" / "3"
    assert document_dir(base, 3, 7) == base / "projects" / "3" / "7"
    assert tmp_dir(base) == base / "tmp"
    assert trash_dir(base) == base / "trash"

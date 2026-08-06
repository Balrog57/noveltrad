"""Unit tests for GFM protection (SDD 10.5)."""

from __future__ import annotations

from noveltrad.modules.documents.gfm import (
    _has_unclosed_fence,
    count_markers,
    protect,
    restore,
    validate,
)


def test_protect_link_destination():
    protected, mapping = protect("See [here](https://example.com/page) and [two](relative/x).")
    assert count_markers(protected) == 2
    assert "https://example.com/page" not in protected
    restored = restore(protected, mapping)
    assert restored == "See [here](https://example.com/page) and [two](relative/x)."


def test_protect_code_fence_content_untouched():
    source = "Text\n```\n[link](https://x.com) NOVELTRAD:deadbeef\n```\nAfter"
    protected, mapping = protect(source)
    assert "https://x.com" in protected
    restored = restore(protected, mapping)
    assert restored == source


def test_validate_ok():
    protected, mapping = protect("[a](https://x.com) [b](relative)")
    assert validate(protected, mapping) == []


def test_validate_missing_marker():
    protected, mapping = protect("[a](https://x.com)")
    errors = validate(protected.replace("[NOVELTRAD:", "[XXXX:"), mapping)
    assert "MISSING" in errors


def test_validate_duplicate_and_order():
    protected, mapping = protect("[a](x) [b](y)")
    duplicated = protected + " " + protected.split(" ")[1]
    errors = validate(duplicated, mapping)
    assert "DUPLICATE" in errors
    swapped = protected.split(" ")[1] + " " + protected.split(" ")[0]
    errors = validate(swapped, mapping)
    assert "UNORDERED" in errors


def test_unclosed_fence_detected():
    assert _has_unclosed_fence("text\n```\nnever closed")
    assert not _has_unclosed_fence("text\n```\nclosed\n```\n")

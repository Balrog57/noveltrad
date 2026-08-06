"""Tests for the OCR module (CDC Phase 3).

Tesseract is not installed on the CI runner, so these tests assert the graceful
degradation: is_available() is False and extract_text() raises OcrUnavailable
with a helpful message.
"""

from __future__ import annotations

import pytest

from src.core import ocr


def test_is_available_returns_bool() -> None:
    """is_available() must not raise even when Tesseract is absent."""
    assert isinstance(ocr.is_available(), bool)


def test_find_tesseract_returns_none_or_path() -> None:
    """find_tesseract() returns None on a clean machine or a valid path."""
    result = ocr.find_tesseract()
    assert result is None or isinstance(result, str)


def test_extract_text_raises_when_unavailable(monkeypatch) -> None:
    """When Tesseract is missing, extract_text raises OcrUnavailable (not a crash)."""
    monkeypatch.setattr(ocr, "find_tesseract", lambda: None)
    with pytest.raises(ocr.OcrUnavailable) as exc_info:
        ocr.extract_text("/nonexistent/image.png")
    assert "Tesseract" in str(exc_info.value) or "OCR" in str(exc_info.value)


def test_install_hint_is_user_facing() -> None:
    """The install hint must contain actionable instructions."""
    hint = ocr.install_hint()
    assert "Tesseract" in hint
    assert "TESSERACT_CMD" in hint or "config.json" in hint

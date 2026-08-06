"""Unit tests for VerificationService (SDD 11.11, 11.12)."""

from __future__ import annotations

from noveltrad.core.contracts import SegmentId
from noveltrad.modules.verification.service import VerificationService


def test_validate_completion_valid(conn):
    service = VerificationService(conn)
    report = service.validate_completion(SegmentId(1), "# Title\n\nSome *text*.")
    assert report.valid
    assert report.error_codes == ()


def test_validate_completion_empty(conn):
    service = VerificationService(conn)
    report = service.validate_completion(SegmentId(1), "")
    assert not report.valid
    assert "EMPTY" in report.error_codes


def test_validate_completion_unclosed_fence(conn):
    service = VerificationService(conn)
    report = service.validate_completion(SegmentId(1), "```python\nx = 1")
    assert not report.valid
    assert "GFM_INVALID" in report.error_codes


def test_validate_translated_segment_markers(conn):
    service = VerificationService(conn)
    source = "[text]([NOVELTRAD:1111111111111111])"
    content = "[text]([NOVELTRAD:1111111111111111])"
    report = service.validate_translated_segment(SegmentId(1), content, source)
    assert report.valid


def test_validate_translated_segment_missing_marker(conn):
    service = VerificationService(conn)
    source = "[a]([NOVELTRAD:1111111111111111]) [b]([NOVELTRAD:2222222222222222])"
    content = "[a]([NOVELTRAD:1111111111111111])"
    report = service.validate_translated_segment(SegmentId(1), content, source)
    assert not report.valid
    assert "MISSING_MARKER" in report.error_codes


def test_validate_import_missing_document(conn):
    service = VerificationService(conn)
    report = service.validate_import(999)
    assert not report.valid

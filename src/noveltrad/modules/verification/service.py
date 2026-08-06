"""VerificationService (SDD 7.18, 11.12).

Validates import results and segment completions. Imports only core types
and the GFM parser; it never imports translation.
"""

from __future__ import annotations

import sqlite3

from noveltrad.core.contracts import DocumentId, SegmentId, ValidationReport

from .gfm import validate_gfm
from .markers import markers_preserved


class VerificationService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def validate_import(self, document_id: DocumentId) -> ValidationReport:
        row = self._conn.execute(
            "SELECT source_path FROM documents WHERE id=?", (document_id,)
        ).fetchone()
        if row is None:
            return ValidationReport(False, ("DOCUMENT_NOT_FOUND",), ("document not found",))
        return ValidationReport(True, (), ())

    def validate_completion(self, segment_id: SegmentId, markdown: str) -> ValidationReport:
        errors: list[str] = []
        messages: list[str] = []
        gfm_errors = validate_gfm(markdown)
        errors.extend(gfm_errors)
        if gfm_errors:
            messages.append("GFM structure is invalid")
        return ValidationReport(
            valid=not errors,
            error_codes=tuple(errors),
            safe_messages=tuple(messages),
        )

    def validate_translated_segment(
        self, segment_id: SegmentId, content: str, source_markdown: str
    ) -> ValidationReport:
        """Validate content against the source markers (11.11)."""
        errors: list[str] = []
        messages: list[str] = []
        marker_errors = markers_preserved(content, source_markdown)
        errors.extend(marker_errors)
        if marker_errors:
            messages.append("markers are not preserved exactly")
        gfm_errors = validate_gfm(content)
        errors.extend(gfm_errors)
        if gfm_errors:
            messages.append("GFM structure is invalid")
        return ValidationReport(
            valid=not errors,
            error_codes=tuple(errors),
            safe_messages=tuple(messages),
        )

"""Response parsing and validation (SDD 11.11).

The expected response is a single UTF-8 JSON object with no leading/trailing
text or fence, with exactly: schema="noveltrad.segment.v1", the same
request_id and segment_id, and a non-empty content string. Parsing is based
on json.JSONDecoder.raw_decode requiring full consumption of the input and
object_pairs_hook rejecting duplicate keys; missing/extra keys, wrong types,
mismatched identifiers, multiple objects or non-UTF-8 bytes are refused.
"""

from __future__ import annotations

import json

from noveltrad.core.contracts import FinishReason, SegmentId
from noveltrad.core.exceptions import ResponseValidationError

_SCHEMA = "noveltrad.segment.v1"


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def parse_segment_response(raw: str, request_id: str, segment_id: SegmentId) -> str:
    """Parse and validate the segment envelope; returns content."""
    try:
        decoded = json.loads(
            raw,
            object_pairs_hook=_reject_duplicates,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise ResponseValidationError("INVALID_JSON", "response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ResponseValidationError("INVALID_OBJECT", "response is not an object")
    schema = decoded.get("schema")
    if schema != _SCHEMA:
        raise ResponseValidationError("WRONG_SCHEMA", "response schema mismatch")
    allowed = {"schema", "request_id", "segment_id", "content"}
    if set(decoded) != allowed:
        raise ResponseValidationError("EXTRA_OR_MISSING_KEY", "response keys mismatch")
    if decoded.get("request_id") != request_id:
        raise ResponseValidationError("REQUEST_ID_MISMATCH", "request id mismatch")
    if decoded.get("segment_id") != segment_id:
        raise ResponseValidationError("SEGMENT_ID_MISMATCH", "segment id mismatch")
    content = decoded.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ResponseValidationError("EMPTY_CONTENT", "content is empty")
    return content


def validate_finish_reason(reason: FinishReason | None) -> None:
    """Only STOP is valid (11.11)."""
    if reason is not FinishReason.STOP:
        raise ResponseValidationError(
            "BAD_FINISH_REASON",
            f"finish reason {reason} is invalid",
        )


def build_envelope(
    request_id: str,
    segment_id: SegmentId,
    stage: str,
    source_language: str,
    target_language: str,
    target_content: str,
    context: dict[str, str | None],
) -> str:
    """Canonical user message (11.11): json.dumps with exact keys."""
    payload = {
        "schema": "noveltrad.request.v1",
        "request_id": request_id,
        "segment_id": segment_id,
        "stage": stage,
        "source_language": source_language,
        "target_language": target_language,
        "target_content": target_content,
        "context": {
            "previous": context.get("previous"),
            "current": context.get("current"),
            "next": context.get("next"),
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

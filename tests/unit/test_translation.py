"""Unit tests for translation core: retry, parser, prompts, segmentation."""

from __future__ import annotations

import pytest

from noveltrad.core.contracts import FinishReason, PipelineStage, SegmentId
from noveltrad.core.exceptions import ContextWindowError, ResponseValidationError
from noveltrad.modules.translation.prompt_loader import PromptLoader
from noveltrad.modules.translation.response_parser import (
    build_envelope,
    parse_segment_response,
    validate_finish_reason,
)
from noveltrad.modules.translation.retry import (
    MAX_RETRIES,
    compute_wait,
    is_retryable_http,
    next_retry_delay,
    parse_retry_after,
)
from noveltrad.modules.translation.segmentation import (
    count_tokens,
    margin,
    output_reserve,
    segment_document,
)

# -- retry (RM-009) ---------------------------------------------------------


def test_retry_delays():
    assert [next_retry_delay(i) for i in range(1, 6)] == [1, 5, 15, 30, 60]
    assert MAX_RETRIES == 5


def test_retryable_http_codes():
    assert is_retryable_http(429)
    assert is_retryable_http(503)
    assert is_retryable_http(500)
    assert not is_retryable_http(404)
    assert not is_retryable_http(401)


def test_parse_retry_after_seconds():
    assert parse_retry_after("30") == 30.0
    assert parse_retry_after("0") == 0.0


def test_parse_retry_after_rejects_huge_and_garbage():
    assert parse_retry_after("999999") is None
    assert parse_retry_after("abc") is None
    assert parse_retry_after(None) is None


def test_parse_retry_after_http_date():
    from datetime import UTC, datetime, timedelta

    future = datetime.now(UTC) + timedelta(seconds=60)
    formatted = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
    seconds = parse_retry_after(formatted)
    assert seconds is not None
    assert 55 <= seconds <= 65


def test_compute_wait_retry_after_only_for_429_503():
    assert compute_wait(1, 10.0, status_code=429) == 10.0
    assert compute_wait(1, 10.0, status_code=503) == 10.0
    assert compute_wait(1, 10.0, status_code=500) == 1.0


# -- parser (11.11) ----------------------------------------------------------


def _valid_response(request_id: str) -> str:
    import json

    return json.dumps(
        {
            "schema": "noveltrad.segment.v1",
            "request_id": request_id,
            "segment_id": 5,
            "content": "Translated text.",
        }
    )


def test_parse_valid_response():
    content = parse_segment_response(_valid_response("req1"), "req1", SegmentId(5))
    assert content == "Translated text."


def test_parse_rejects_fenced_json():
    fenced = "```json\n" + _valid_response("req1") + "\n```"
    with pytest.raises(ResponseValidationError):
        parse_segment_response(fenced, "req1", SegmentId(5))


def test_parse_rejects_duplicate_keys():
    with pytest.raises(ResponseValidationError):
        parse_segment_response(
            '{"schema":"noveltrad.segment.v1","schema":"noveltrad.segment.v1",'
            '"request_id":"r","segment_id":1,"content":"x"}',
            "r",
            SegmentId(1),
        )


def test_parse_rejects_mismatched_ids():
    with pytest.raises(ResponseValidationError):
        parse_segment_response(_valid_response("other"), "req1", SegmentId(5))
    with pytest.raises(ResponseValidationError):
        parse_segment_response(
            _valid_response("req1").replace('"segment_id": 5', '"segment_id": 6'),
            "req1",
            SegmentId(5),
        )


def test_parse_rejects_empty_content():
    import json

    payload = {
        "schema": "noveltrad.segment.v1",
        "request_id": "r",
        "segment_id": 1,
        "content": "   ",
    }
    with pytest.raises(ResponseValidationError):
        parse_segment_response(json.dumps(payload), "r", SegmentId(1))


def test_finish_reason_validation():
    validate_finish_reason(FinishReason.STOP)
    for reason in (FinishReason.LENGTH, FinishReason.CONTENT_FILTER, FinishReason.OTHER):
        with pytest.raises(ResponseValidationError):
            validate_finish_reason(reason)


def test_build_envelope_canonical():
    envelope = build_envelope("req1", SegmentId(3), "translate", "en", "fr", "Hello", {})
    import json

    parsed = json.loads(envelope)
    assert parsed["schema"] == "noveltrad.request.v1"
    assert parsed["target_content"] == "Hello"
    assert parsed["context"] == {"previous": None, "current": None, "next": None}


# -- prompts (11.11) ----------------------------------------------------------


def test_prompt_bundle_has_four_files():
    loader = PromptLoader("v1")
    for stage in (
        PipelineStage.TRANSLATE,
        PipelineStage.REVISE,
        PipelineStage.CONTEXT,
        PipelineStage.POLISH,
    ):
        prompt = loader.load(stage)
        assert "NOVELTRAD" in prompt
        assert "target_content" in prompt


# -- segmentation (11.10, 11.14) -----------------------------------------------


def test_count_tokens_utf8():
    assert count_tokens("hello") == 5
    assert count_tokens("héllo") == 6


def test_margin_and_reserve():
    assert margin(8000) == 800
    assert margin(1000) == 512
    assert output_reserve(100, 4096) == 512  # max(512, ceil(1.5*100)+64)
    assert output_reserve(10000, 20000) == 15064  # max(512, 15000+64)


def test_segment_single():
    segments = segment_document(
        "Short text here.",
        window_tokens=8000,
        prompt_tokens=500,
        max_output_tokens=1024,
    )
    assert len(segments) == 1
    assert segments[0].text == "Short text here."


def test_segment_split():
    text = "\n\n".join(f"Paragraph {i} with some content." for i in range(40))
    segments = segment_document(
        text,
        window_tokens=1500,
        prompt_tokens=300,
        max_output_tokens=512,
    )
    assert len(segments) > 1
    # reconstruction preserves order
    rebuilt = "\n\n".join(s.text for s in segments)
    assert rebuilt == text


def test_segment_too_large_dialogue():
    with pytest.raises(ContextWindowError):
        segment_document(
            "— " + "x" * 10000,
            window_tokens=500,
            prompt_tokens=100,
            max_output_tokens=128,
        )

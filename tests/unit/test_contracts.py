"""Unit tests for core.contracts and exceptions (SDD 7.18)."""

from __future__ import annotations

import pytest

from noveltrad.core.contracts import (
    FinishReason,
    JobState,
    PipelineStage,
    ProjectStatus,
    SegmentState,
)
from noveltrad.core.exceptions import (
    AuthenticationError,
    BusinessError,
    ConflictError,
    ContextWindowError,
    ImportConversionError,
    IntegrityError,
    LockedError,
    NotFoundError,
    NovelTradError,
    ProviderError,
    ResponseValidationError,
    StorageError,
    ValidationError,
)


def test_enums_have_exact_values():
    assert ProjectStatus.COMPLETED.value == "Completed"
    assert JobState.RETRYING.value == "Retrying"
    assert SegmentState.COHERENCE_CHECKED.value == "COHERENCE_CHECKED"
    assert PipelineStage.POLISH.value == "polish"
    assert FinishReason.STOP.value == "stop"


def test_taxonomy_root_and_branches():
    business = [ValidationError, NotFoundError, ConflictError, LockedError, AuthenticationError]
    technical = [
        StorageError,
        IntegrityError,
        ImportConversionError,
        ContextWindowError,
        ProviderError,
        ResponseValidationError,
    ]
    for cls in business + technical:
        assert issubclass(cls, NovelTradError)
    for cls in business:
        assert issubclass(cls, BusinessError)


def test_provider_error_carries_metadata():
    error = ProviderError("RATE_LIMITED", recoverable=True, retry_after_seconds=30.0)
    assert error.error_code == "RATE_LIMITED"
    assert error.recoverable is True
    assert error.retry_after_seconds == 30.0
    assert error.safe_message == "RATE_LIMITED"


def test_response_validation_error_is_recoverable():
    error = ResponseValidationError("INVALID_JSON")
    assert error.recoverable is True


def test_contracts_frozen():
    from noveltrad.core.contracts import Job

    job = Job(
        id=1,
        document_id=2,
        state=JobState.QUEUED,
        progress=0.0,
        current_stage=None,
        current_segment_id=None,
        snapshot=None,
        next_retry_at=None,
    )
    with pytest.raises(AttributeError):
        job.id = 99


def test_progress_phases_complete():
    from noveltrad.core.contracts import ProgressPhase

    values = {p.value for p in ProgressPhase}
    assert values == {
        "import_copy",
        "import_inspect",
        "import_convert",
        "import_validate",
        "import_publish",
        "export_validate",
        "export_assemble",
        "export_archive",
        "export_finalize",
    }

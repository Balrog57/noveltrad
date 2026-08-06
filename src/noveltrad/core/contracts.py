"""Normative public types and service protocols (SDD 7.18).

This module is the single source of truth for the public contracts used
across NovelTrad. It must stay importable without any third-party dependency.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import BinaryIO, Literal, NewType, Protocol

ProjectId = NewType("ProjectId", int)
DocumentId = NewType("DocumentId", int)
ChapterId = NewType("ChapterId", int)
SegmentId = NewType("SegmentId", int)
JobId = NewType("JobId", int)
ArtifactId = NewType("ArtifactId", str)
CorrelationId = NewType("CorrelationId", str)
LanguageCode = NewType("LanguageCode", str)
SafeScalar = str | int | float | bool | None
SafeFields = tuple[tuple[str, SafeScalar], ...]


class ProviderName(StrEnum):
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    OPENAI_COMPATIBLE = "openai_compatible"


class PipelineStage(StrEnum):
    TRANSLATE = "translate"
    REVISE = "revise"
    CONTEXT = "context"
    POLISH = "polish"


class ProjectStatus(StrEnum):
    DRAFT = "Draft"
    READY = "Ready"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"


class DocumentStatus(StrEnum):
    TO_TRANSLATE = "ToTranslate"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"


class JobState(StrEnum):
    WAITING = "Waiting"
    QUEUED = "Queued"
    RUNNING = "Running"
    PAUSED = "Paused"
    RETRYING = "Retrying"
    COMPLETED = "Completed"
    FAILED = "Failed"


class SegmentState(StrEnum):
    PENDING = "PENDING"
    TRANSLATED = "TRANSLATED"
    REVISED = "REVISED"
    COHERENCE_CHECKED = "COHERENCE_CHECKED"
    POLISHED = "POLISHED"


class FinishReason(StrEnum):
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALL = "tool_call"
    OTHER = "other"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ProgressPhase(StrEnum):
    IMPORT_COPY = "import_copy"
    IMPORT_INSPECT = "import_inspect"
    IMPORT_CONVERT = "import_convert"
    IMPORT_VALIDATE = "import_validate"
    IMPORT_PUBLISH = "import_publish"
    EXPORT_VALIDATE = "export_validate"
    EXPORT_ASSEMBLE = "export_assemble"
    EXPORT_ARCHIVE = "export_archive"
    EXPORT_FINALIZE = "export_finalize"


@dataclass(frozen=True, slots=True)
class Project:
    id: ProjectId
    name: str
    source_language: LanguageCode | Literal["mul"] | None
    target_language: LanguageCode
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Document:
    id: DocumentId
    project_id: ProjectId
    display_name: str
    order_index: int
    status: DocumentStatus
    progress: float
    word_count: int
    character_count: int
    detected_language: LanguageCode | Literal["und"] | None


@dataclass(frozen=True, slots=True)
class Chapter:
    id: ChapterId
    document_id: DocumentId
    order_index: int
    title: str | None


@dataclass(frozen=True, slots=True)
class EditableChapter:
    chapter_id: ChapterId
    markdown: str
    content_hash: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ImportSource:
    filename: str
    size_bytes: int
    stream: BinaryIO


@dataclass(frozen=True, slots=True)
class ImportFailure:
    filename: str
    error_code: str
    safe_message: str


@dataclass(frozen=True, slots=True)
class ImportBatchResult:
    documents: tuple[Document, ...]
    failures: tuple[ImportFailure, ...]


@dataclass(frozen=True, slots=True)
class PipelineSnapshot:
    provider: ProviderName
    base_url: str
    model: str
    context_window_tokens: int
    tokenizer_id: str
    temperature: float
    max_output_tokens: int
    seed: int | None
    prompt_bundle_version: str
    response_schema_version: str
    snapshot_hash: str


@dataclass(frozen=True, slots=True)
class Job:
    id: JobId
    document_id: DocumentId
    state: JobState
    progress: float
    current_stage: PipelineStage | None
    current_segment_id: SegmentId | None
    snapshot: PipelineSnapshot
    next_retry_at: datetime | None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    valid: bool
    error_codes: tuple[str, ...]
    safe_messages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectProgress:
    project_id: ProjectId
    project_status: ProjectStatus
    active_job: Job | None
    completed_documents: int
    total_documents: int
    elapsed_seconds: float
    estimated_remaining_seconds: float | None


@dataclass(frozen=True, slots=True)
class SearchReplacePreview:
    token: str
    occurrences: int
    document_ids: tuple[DocumentId, ...]
    chapter_ids: tuple[ChapterId, ...]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    id: ArtifactId
    download_name: str
    media_type: str
    size_bytes: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class SettingsView:
    ui_language: Literal["fr", "en"]
    theme: Literal["light", "dark", "sepia"]
    completion_sound_enabled: bool
    provider: ProviderName | None
    base_url: str | None
    api_key_configured: bool
    model: str | None
    context_window_tokens: int | None
    temperature: float
    max_output_tokens: int | None
    seed: int | None


@dataclass(frozen=True, slots=True)
class SettingsUpdate:
    ui_language: Literal["fr", "en"]
    theme: Literal["light", "dark", "sepia"]
    completion_sound_enabled: bool
    provider: ProviderName | None
    base_url: str | None
    model: str | None
    context_window_tokens: int | None
    temperature: float
    max_output_tokens: int | None
    seed: int | None
    api_key_action: Literal["KEEP", "REPLACE", "DELETE"]
    api_key_value: str | None


@dataclass(frozen=True, slots=True)
class LogEntry:
    created_at: datetime
    level: LogLevel
    event: str
    correlation_id: CorrelationId
    error_code: str | None
    safe_message: str
    project_id: ProjectId | None
    document_id: DocumentId | None
    job_id: JobId | None
    fields: SafeFields


@dataclass(frozen=True, slots=True)
class LogContext:
    correlation_id: CorrelationId
    project_id: ProjectId | None = None
    document_id: DocumentId | None = None
    job_id: JobId | None = None


@dataclass(frozen=True, slots=True)
class CompletionRequest:
    request_id: str
    segment_id: SegmentId
    stage: PipelineStage
    system_prompt: str
    payload_json: str
    model: str
    temperature: float
    max_output_tokens: int


@dataclass(frozen=True, slots=True)
class CompletionResponse:
    text: str
    finish_reason: FinishReason
    input_tokens: int | None
    output_tokens: int | None
    retry_after_seconds: float | None
    provider_request_id: str | None


@dataclass(frozen=True, slots=True)
class PipelineResult:
    job_id: JobId
    completed: bool
    first_unvalidated_segment_id: SegmentId | None


@dataclass(frozen=True, slots=True)
class ProgressUpdate:
    phase: ProgressPhase
    completed_units: int
    total_units: int | None
    message_key: str


class ProgressSink(Protocol):
    def __call__(self, update: ProgressUpdate) -> None: ...


class ProjectService(Protocol):
    def create(self, name: str, target_language: LanguageCode) -> Project: ...
    def get(self, project_id: ProjectId) -> Project: ...
    def list(self, query: str | None = None) -> tuple[Project, ...]: ...
    def rename(self, project_id: ProjectId, name: str) -> Project: ...
    def validate(self, project_id: ProjectId) -> ValidationReport: ...
    def delete(self, project_id: ProjectId, confirmation: str) -> None: ...
    def claim_completion_notice(self, project_id: ProjectId) -> bool: ...
    def acknowledge_completion_notice(self, project_id: ProjectId) -> None: ...


class DocumentService(Protocol):
    def import_batch(
        self,
        project_id: ProjectId,
        sources: Sequence[ImportSource],
        progress: ProgressSink | None = None,
    ) -> ImportBatchResult: ...
    def list(self, project_id: ProjectId) -> tuple[Document, ...]: ...
    def list_chapters(self, document_id: DocumentId) -> tuple[Chapter, ...]: ...
    def load_editable_chapter(self, chapter_id: ChapterId) -> EditableChapter: ...
    def reorder(
        self, project_id: ProjectId, document_ids: Sequence[DocumentId]
    ) -> tuple[Document, ...]: ...
    def delete(self, document_id: DocumentId, confirmation: str | None) -> None: ...
    def save_editable_chapter(
        self, chapter_id: ChapterId, markdown: str, expected_hash: str
    ) -> EditableChapter: ...
    def preview_replace(
        self, project_id: ProjectId, needle: str, replacement: str
    ) -> SearchReplacePreview: ...
    def apply_replace(
        self, project_id: ProjectId, preview_token: str, confirmation: Literal["APPLY_REPLACE"]
    ) -> int: ...


class JobService(Protocol):
    def enqueue_project(
        self, project_id: ProjectId, snapshot: PipelineSnapshot
    ) -> tuple[Job, ...]: ...
    def request_pause(self, project_id: ProjectId) -> None: ...
    def resume(self, job_id: JobId) -> Job: ...
    def restart_with_current_configuration(self, job_id: JobId, confirmation: str) -> Job: ...
    def take_next(self) -> Job | None: ...
    def apply_pause(self, job_id: JobId) -> Job: ...
    def mark_completed(self, job_id: JobId) -> Job: ...
    def mark_failed(self, job_id: JobId, error_code: str) -> Job: ...
    def recover_interrupted(self) -> None: ...
    def get_progress(self, project_id: ProjectId) -> ProjectProgress: ...


class TranslationService(Protocol):
    async def execute(self, job_id: JobId) -> PipelineResult: ...


class VerificationService(Protocol):
    def validate_import(self, document_id: DocumentId) -> ValidationReport: ...
    def validate_completion(self, segment_id: SegmentId, markdown: str) -> ValidationReport: ...


class ExportService(Protocol):
    def generate(
        self, project_id: ProjectId, progress: ProgressSink | None = None
    ) -> ExportArtifact: ...
    def open(self, artifact_id: ArtifactId) -> BinaryIO: ...
    def cleanup(self, artifact_id: ArtifactId) -> None: ...


class SettingsService(Protocol):
    def get_masked(self) -> SettingsView: ...
    def update(self, values: SettingsUpdate) -> SettingsView: ...
    async def validate_configuration(self) -> ValidationReport: ...
    async def list_models(self) -> tuple[str, ...]: ...


class LogService(Protocol):
    def record(
        self,
        level: LogLevel,
        event: str,
        safe_message: str,
        context: LogContext,
        *,
        error_code: str | None = None,
        fields: SafeFields = (),
    ) -> None: ...
    def query(
        self,
        *,
        level: LogLevel | None = None,
        project_id: ProjectId | None = None,
        correlation_id: CorrelationId | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[LogEntry, ...]: ...

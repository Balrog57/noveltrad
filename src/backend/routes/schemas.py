"""Pydantic request/response models for the backend HTTP API.

Schemas are defined here (instead of inline in ``server.py``) so that
``create_app`` stays a thin assembler and individual route modules can
import them without taking a circular dependency on the app factory.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


def build_schemas() -> dict[str, Any]:
    """Return the full set of pydantic models used by the API.

    Built lazily so the heavy ``pydantic`` import only happens when the
    backend actually starts (or a test instantiates the app).
    """

    class ProjectCreateRequest(BaseModel):
        """Minimal project creation — just a name and a working directory.

        Source files are added later via the Pipeline tab or
        ``POST /projects/{id}/translate`` with ``source_paths``.

        The legacy ``source_path`` / ``source_paths`` / ``parse`` fields
        are kept for backward compatibility with the older GUI.
        """
        name: str | None = None          # human-readable project name (v4.2+)
        project_id: str | None = None
        project_dir: str
        # Legacy translation-kickoff fields (kept for old GUI / CLI).
        source_path: str | None = None
        source_paths: list[str] = Field(default_factory=list)
        source_lang: str = "auto"
        target_lang: str = "fr"
        output_path: str | None = None
        output_format: str = Field(default="txt", pattern=r"^(epub|epub_bilingual|docx|srt|txt)$")
        parse: bool = True
        profile: str = Field(default="balanced", pattern=r"^(eco|balanced|premium)$")

    class ProjectUpdateRequest(BaseModel):
        """Minimal project update — rename or change working directory."""
        name: str | None = None
        project_dir: str | None = None

    class ProjectStateResponse(BaseModel):
        project_id: str
        status: str
        source_lang: str
        target_lang: str
        started_at: float
        source_path: str | None = None
        source_paths: list[str] = Field(default_factory=list)
        profile: str = "balanced"
        output_format: str = "txt"

    class ProjectQueueEntry(BaseModel):
        project_id: str
        source_path: str | None = None
        source_paths: list[str] = Field(default_factory=list)
        profile: str = "balanced"

    class PipelineStateResponse(BaseModel):
        project: ProjectStateResponse | None
        state_store: dict[str, Any]
        workers: dict[str, Any]
        paused_stages: list[str]
        pending_hltl: int
        event_log_tail: list[dict[str, Any]]
        output_artifact: dict[str, Any] | None = None
        project_manifest_path: str | None = None
        project_queue: list[ProjectQueueEntry] = Field(default_factory=list)
        project_queue_size: int = 0

    class HITLResponseRequest(BaseModel):
        request_id: str
        answer: str = Field(..., min_length=1)

    class ChunkSubmitRequest(BaseModel):
        chunks: list[dict[str, Any]]

    class AssembleRequest(BaseModel):
        output_path: str
        format: str = "txt"

    class LexiconTermCreate(BaseModel):
        source: str
        target: str
        aliases: list[str] | None = None
        category: str | None = None
        gender: str = "unknown"
        confidence: float = 0.5
        notes: str | None = None
        validated_by_user: bool = False
        chapter_id: str | None = None

    class ReplayChunksRequest(BaseModel):
        chunk_ids: list[str] = Field(..., min_length=1)

    return {
        "ProjectCreateRequest": ProjectCreateRequest,
        "ProjectUpdateRequest": ProjectUpdateRequest,
        "ProjectQueueEntry": ProjectQueueEntry,
        "ProjectStateResponse": ProjectStateResponse,
        "PipelineStateResponse": PipelineStateResponse,
        "HITLResponseRequest": HITLResponseRequest,
        "ChunkSubmitRequest": ChunkSubmitRequest,
        "AssembleRequest": AssembleRequest,
        "LexiconTermCreate": LexiconTermCreate,
        "ReplayChunksRequest": ReplayChunksRequest,
    }


__all__ = ["build_schemas"]

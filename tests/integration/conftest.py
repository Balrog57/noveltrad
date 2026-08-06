"""Integration fixtures: full wiring for end-to-end tests."""

from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import pytest

from noveltrad.core.contracts import (
    CompletionResponse,
    FinishReason,
    ImportSource,
    PipelineSnapshot,
)
from noveltrad.core.database import initialize_schema
from noveltrad.core.logging import LogService
from noveltrad.modules.documents.repository import DocumentRepository
from noveltrad.modules.documents.service import DocumentService
from noveltrad.modules.export.service import ExportService
from noveltrad.modules.jobs.repository import JobRepository
from noveltrad.modules.jobs.service import JobService
from noveltrad.modules.projects.repository import ProjectRepository
from noveltrad.modules.projects.service import ProjectService
from noveltrad.modules.translation.pipeline import TranslationService
from noveltrad.modules.translation.prompt_loader import PromptLoader
from noveltrad.modules.verification.service import VerificationService


class FakeProvider:
    """Deterministic provider double (17.11): echoes target_content."""

    def __init__(self, responses: list[CompletionResponse] | None = None) -> None:
        self.responses = responses or []
        self.calls: list[object] = []

    async def complete(self, request) -> CompletionResponse:
        import json

        self.calls.append(request)
        if self.responses:
            return self.responses.pop(0)
        payload = json.loads(request.payload_json)
        text = payload["target_content"]
        return CompletionResponse(
            text=json.dumps(
                {
                    "schema": "noveltrad.segment.v1",
                    "request_id": request.request_id,
                    "segment_id": request.segment_id,
                    "content": text,
                }
            ),
            finish_reason=FinishReason.STOP,
            input_tokens=10,
            output_tokens=10,
            retry_after_seconds=None,
            provider_request_id="fake",
        )

    async def close(self) -> None:
        pass


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "it.sqlite"


@pytest.fixture
def db(db_path: Path):
    database = initialize_schema(db_path)
    yield database
    database.close()


@pytest.fixture
def conn(db) -> sqlite3.Connection:
    return db.conn


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    base = tmp_path / "data"
    base.mkdir()
    for sub in ("tmp", "trash", "backups", "projects"):
        (base / sub).mkdir()
    return base


@pytest.fixture
def services(conn: sqlite3.Connection, data_dir: Path):
    logs = LogService(conn)
    projects = ProjectService(conn, ProjectRepository(conn), logs, data_dir)
    documents = DocumentService(conn, DocumentRepository(conn), logs, data_dir)
    jobs = JobService(conn, JobRepository(conn), logs)
    export = ExportService(conn, logs, data_dir)
    verification = VerificationService(conn)
    return {
        "projects": projects,
        "documents": documents,
        "jobs": jobs,
        "export": export,
        "verification": verification,
        "logs": logs,
        "conn": conn,
        "data_dir": data_dir,
    }


def snapshot(provider: str = "ollama") -> PipelineSnapshot:
    import hashlib

    return PipelineSnapshot(
        provider=provider,
        base_url="http://localhost:11434",
        model="qwen2.5",
        context_window_tokens=8192,
        tokenizer_id="utf8-bytes-v1",
        temperature=0.2,
        max_output_tokens=2048,
        seed=None,
        prompt_bundle_version="v1",
        response_schema_version="v1",
        snapshot_hash=hashlib.sha256(b"x").hexdigest(),
    )


def source(name: str, content: str) -> ImportSource:
    return ImportSource(
        filename=name,
        size_bytes=len(content.encode("utf-8")),
        stream=io.BytesIO(content.encode("utf-8")),
    )


def make_translation_service(
    conn: sqlite3.Connection, data_dir: Path, provider: FakeProvider | None = None
) -> TranslationService:
    logs = LogService(conn)
    return TranslationService(
        conn,
        provider or FakeProvider(),
        logs,
        data_dir,
        prompt_loader=PromptLoader(),
        sleep=lambda seconds: _noop_sleep(seconds),
    )


async def _noop_sleep(seconds: float) -> None:
    return None

"""End-to-end integration: import -> pipeline -> export (17.3, IT-EF-008)."""

from __future__ import annotations

import zipfile

import pytest

from noveltrad.core.contracts import LanguageCode
from noveltrad.modules.translation.pipeline import TranslationService

from .conftest import make_translation_service, snapshot, source


def _create_project_with_doc(services) -> int:
    project = services["projects"].create("Integration", LanguageCode("fr"))
    result = services["documents"].import_batch(
        project.id,
        [source("chap.txt", "Hello world.\n\nSecond paragraph here.")],
    )
    assert len(result.documents) == 1
    return project.id


@pytest.mark.asyncio
async def test_full_pipeline(services):
    project_id = _create_project_with_doc(services)
    jobs = services["jobs"].enqueue_project(project_id, snapshot())
    assert jobs[0].state.value == "Queued"

    taken = services["jobs"].take_next()
    assert taken is not None

    service: TranslationService = make_translation_service(
        services["conn"], services["data_dir"]
    )
    result = await service.execute(taken.id)
    assert result.completed is True

    completed = services["jobs"].mark_completed(taken.id)
    assert completed.state.value == "Completed"
    assert services["conn"].execute(
        "SELECT status FROM projects WHERE id=?", (project_id,)
    ).fetchone()[0] == "Completed"


@pytest.mark.asyncio
async def test_pipeline_writes_translated_file(services):
    project_id = _create_project_with_doc(services)
    services["jobs"].enqueue_project(project_id, snapshot())
    taken = services["jobs"].take_next()
    service = make_translation_service(services["conn"], services["data_dir"])
    await service.execute(taken.id)
    services["jobs"].mark_completed(taken.id)

    document = services["documents"].list(project_id)[0]
    from noveltrad.core.paths import document_dir

    translated = document_dir(services["data_dir"], project_id, document.id) / "translated.md"
    assert translated.exists()
    assert "Hello world." in translated.read_text(encoding="utf-8")
    assert services["conn"].execute(
        "SELECT translated_hash FROM documents WHERE id=?", (document.id,)
    ).fetchone()[0] is not None


@pytest.mark.asyncio
async def test_pipeline_segments_are_sequential(services):
    project_id = _create_project_with_doc(services)
    services["jobs"].enqueue_project(project_id, snapshot())
    taken = services["jobs"].take_next()

    fake = None
    from tests.integration.conftest import FakeProvider

    fake = FakeProvider()
    service = make_translation_service(services["conn"], services["data_dir"], fake)
    await service.execute(taken.id)

    stages = [call.stage.value for call in fake.calls]
    # Four passes, same model, one call per segment per pass in order
    assert stages == ["translate", "revise", "context", "polish"]


@pytest.mark.asyncio
async def test_export_zip_contains_markdown(services):
    project_id = _create_project_with_doc(services)
    services["jobs"].enqueue_project(project_id, snapshot())
    taken = services["jobs"].take_next()
    service = make_translation_service(services["conn"], services["data_dir"])
    result = await service.execute(taken.id)
    assert result.completed is True
    services["jobs"].mark_completed(taken.id)

    artifact = services["export"].generate(project_id)
    path = services["export"].open(artifact.id)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert any(name.endswith(".md") for name in names)
    services["export"].cleanup(artifact.id)


def test_pause_resume_flow(services):
    project_id = _create_project_with_doc(services)
    services["jobs"].enqueue_project(project_id, snapshot())
    services["jobs"].request_pause(project_id)
    taken = services["jobs"].take_next()
    assert taken.state.value == "Paused"
    resumed = services["jobs"].resume(taken.id)
    assert resumed.state.value == "Queued"


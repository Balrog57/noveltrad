"""Project view: the single continuous journey (SDD 13.5).

Create/open -> drop files -> convert & check -> reorder -> confirm target
and provider/model -> validate preparation -> launch -> follow/pause ->
resume -> edit after completion -> export. Satisfied steps stay visible;
one primary action per state.
"""

from __future__ import annotations

import io

import streamlit as st

from noveltrad.core.contracts import (
    ImportSource,
    PipelineSnapshot,
    ProjectStatus,
)
from noveltrad.ui.i18n import translate


def render(container, session) -> None:
    language = session.language
    t = lambda key: translate(key, language)  # noqa: E731
    project_id = session.current_project_id
    if project_id is None:
        st.info(t("project.empty"))
        return

    project_service = container.project_service
    document_service = container.document_service
    job_service = container.job_service
    settings_service = container.settings_service

    try:
        project = project_service.get(project_id)
    except Exception:  # noqa: BLE001
        st.error("project not found")
        session.current_project_id = None
        return

    st.title(f"{project.name} — {project.status.value}")

    # -- import zone ------------------------------------------------------
    if project.status in (ProjectStatus.DRAFT, ProjectStatus.READY, ProjectStatus.FAILED):
        with st.expander(t("project.upload"), expanded=True):
            st.caption(t("project.upload_hint"))
            uploaded = st.file_uploader(
                t("project.upload"),
                type=["epub", "docx", "txt", "md", "srt"],
                accept_multiple_files=True,
                key="file_uploader",
            )
            if uploaded and st.button("Import", key="import_btn"):
                sources = [
                    ImportSource(
                        filename=file.name,
                        size_bytes=file.size or 0,
                        stream=io.BytesIO(file.getvalue()),
                    )
                    for file in uploaded
                ]
                result = document_service.import_batch(project_id, sources)
                for failure in result.failures:
                    st.error(f"{failure.filename}: {failure.error_code}")
                if result.documents:
                    st.success(f"{len(result.documents)} document(s) imported")
                st.rerun()

    # -- document table ---------------------------------------------------
    documents = document_service.list(project_id)
    if documents:
        st.subheader(t("project.docs"))
        for doc in documents:
            with st.container(border=True):
                cols = st.columns([3, 2, 1, 1, 1])
                cols[0].markdown(f"**{doc.display_name}**")
                cols[1].markdown(f"{t('doc.status')}: {doc.status.value} ({doc.progress:.0f}%)")
                cols[2].markdown(f"{doc.word_count} {t('doc.words')}")
                cols[3].markdown(doc.detected_language or "?")
                if cols[4].button(t("doc.delete"), key=f"del_{doc.id}"):
                    try:
                        document_service.delete(doc.id, None)
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))

    # -- primary action ---------------------------------------------------
    settings = settings_service.get_masked()
    if project.status == ProjectStatus.DRAFT:
        report = project_service.validate(project_id)
        if report.valid:
            if st.button(t("project.validate"), key="validate_btn"):
                project_service.validate(project_id)
                st.rerun()
        else:
            for message in report.safe_messages:
                st.warning(message)
    elif project.status == ProjectStatus.READY:
        if st.button(t("project.launch"), key="launch_btn"):
            snapshot = _snapshot_from_settings(settings)
            job_service.enqueue_project(project_id, snapshot)
            st.rerun()
    elif project.status in (ProjectStatus.RUNNING, ProjectStatus.PAUSED):
        progress = job_service.get_progress(project_id)
        st.progress(progress.completed_documents / max(1, progress.total_documents))
        st.caption(f"{progress.completed_documents}/{progress.total_documents} {t('project.docs')}")
        if project.status == ProjectStatus.RUNNING:
            if st.button(t("project.pause"), key="pause_btn"):
                job_service.request_pause(project_id)
                st.rerun()
        else:
            if st.button(t("project.resume"), key="resume_btn"):
                jobs = job_service._repo.list_by_project(project_id)
                for job in jobs:
                    if job.state.value == "Paused":
                        job_service.resume(job.id)
                st.rerun()
    elif project.status == ProjectStatus.COMPLETED:
        st.success(t("project.completed"))
        if st.button(t("project.export"), key="export_btn"):
            try:
                artifact = container.export_service.generate(project_id)
                path = container.export_service.open(artifact.id)
                st.download_button(
                    t("project.export"),
                    data=path.read_bytes(),
                    file_name=artifact.download_name,
                    mime=artifact.media_type,
                    key="export_dl",
                )
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
    elif project.status == ProjectStatus.FAILED:
        st.error(t("project.failed"))
        if st.button(t("project.resume"), key="resume_failed_btn"):
            jobs = job_service._repo.list_by_project(project_id)
            for job in jobs:
                if job.state.value == "Failed":
                    job_service.resume(job.id)
            st.rerun()

    # -- completion notice (13.5) ------------------------------------------
    if project.status == ProjectStatus.COMPLETED:
        claimed = project_service.claim_completion_notice(project_id)
        if claimed:
            from noveltrad.ui.notifications import completion_fragment

            st.components.v1.html(
                completion_fragment(
                    True,
                    settings.completion_sound_enabled,
                    t("project.completed"),
                ),
                height=0,
            )
            st.toast(t("project.completed"))
        else:
            st.info(t("project.completed"))


def _snapshot_from_settings(settings) -> PipelineSnapshot:
    window = settings.context_window_tokens or 8192
    return PipelineSnapshot(
        provider=settings.provider,
        base_url=settings.base_url or "",
        model=settings.model or "",
        context_window_tokens=window,
        tokenizer_id="utf8-bytes-v1",
        temperature=settings.temperature,
        max_output_tokens=settings.max_output_tokens or 2048,
        seed=settings.seed,
        prompt_bundle_version="v1",
        response_schema_version="v1",
        snapshot_hash=_hash(settings),
    )


def _hash(settings) -> str:
    import hashlib
    import json

    payload = {
        "provider": str(settings.provider),
        "base_url": settings.base_url,
        "model": settings.model,
        "window": settings.context_window_tokens,
        "temperature": settings.temperature,
        "max_output": settings.max_output_tokens,
        "seed": settings.seed,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

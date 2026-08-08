"""Project view: the single continuous journey (SDD 13.5).

Create/open -> drop files -> convert & check -> reorder -> confirm target
and provider/model -> validate preparation -> launch -> follow/pause ->
resume -> edit after completion -> export. Satisfied steps stay visible;
one primary action per state.
"""

from __future__ import annotations

import contextlib
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

    # back to project list
    if st.button("← " + t("nav.projects"), key="back_to_list_btn"):
        session.current_project_id = None
        st.rerun()

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
        _handle_reorder_param(container, session, project_id, documents)
        _render_documents(container, session, project_id, documents)

    # -- primary action ---------------------------------------------------
    settings = settings_service.get_masked()
    if project.status == ProjectStatus.DRAFT:
        report = project_service.validate(project_id)
        if report.valid:
            if st.button(t("project.validate"), key="validate_btn"):
                try:
                    project_service.mark_ready(project_id)
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
        else:
            for message in report.safe_messages:
                st.warning(message)
    elif project.status == ProjectStatus.READY:
        missing_ai = settings.provider is None or not settings.base_url or not settings.model
        if missing_ai:
            st.warning(t("settings.title") + ": " + t("project.need_ai_config"))
        if st.button(
            t("project.launch"),
            key="launch_btn",
            disabled=missing_ai,
            help=t("settings.title") + ": " + t("project.need_ai_config") if missing_ai else None,
        ) and not missing_ai:
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
        _render_editor(container, session, project_id, document_service)
        _render_replace(container, session, project_id, document_service)
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


def _render_editor(container, session, project_id, document_service) -> None:
    """One-chapter Markdown editor after final validation (13.5, EF-011)."""
    language = session.language
    t = lambda key: translate(key, language)  # noqa: E731
    st.divider()
    st.subheader(t("editor.title"))
    documents = document_service.list(project_id)
    if not documents:
        return
    chapter_options: dict[str, int] = {}
    for doc in documents:
        for chapter in document_service.list_chapters(doc.id):
            title = chapter.title or t("editor.title")
            label = f"{doc.display_name} — {title} (#{chapter.order_index})"
            chapter_options[label] = chapter.id
    if not chapter_options:
        return
    selected = st.selectbox(t("editor.title"), list(chapter_options.keys()), key="editor_chapter")
    chapter_id = chapter_options[selected]
    state_key = f"editor_text_{chapter_id}"
    if state_key not in st.session_state:
        try:
            editable = document_service.load_editable_chapter(chapter_id)
            st.session_state[state_key] = editable.markdown
            st.session_state[f"editor_hash_{chapter_id}"] = editable.content_hash
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
            return
    content = st.text_area(
        t("editor.preview"),
        value=st.session_state.get(state_key, ""),
        height=400,
        key=f"editor_area_{chapter_id}",
    )
    if content != st.session_state.get(state_key):
        st.session_state[state_key] = content
        st.caption(t("editor.autosaved"))
    if st.button(t("editor.save"), key=f"editor_save_{chapter_id}"):
        try:
            expected = st.session_state.get(f"editor_hash_{chapter_id}", "")
            editable = document_service.save_editable_chapter(chapter_id, content, expected)
            st.session_state[f"editor_hash_{chapter_id}"] = editable.content_hash
            st.success(t("editor.save"))
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))


def _render_replace(container, session, project_id, document_service) -> None:
    """Global search & replace on finalized translated.md (13.5, EF-012)."""
    language = session.language
    t = lambda key: translate(key, language)  # noqa: E731
    st.divider()
    st.subheader(t("replace.preview"))
    with st.container(border=True):
        needle = st.text_input(t("replace.preview"), key="replace_needle")
        replacement = st.text_input(t("replace.apply"), key="replace_replacement")
        if st.button(t("replace.preview"), key="replace_preview_btn"):
            try:
                preview = document_service.preview_replace(project_id, needle, replacement)
                session.replace_token = preview.token
                st.info(f"{preview.occurrences} — {len(preview.document_ids)} {t('project.docs')}")
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
        confirmation = st.text_input(t("replace.token"), key="replace_token_input")
        if st.button(t("replace.apply"), key="replace_apply_btn"):
            try:
                applied = document_service.apply_replace(
                    project_id, session.replace_token or "", confirmation
                )
                st.success(f"{applied} {t('replace.apply')}")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))


def _handle_reorder_param(container, session, project_id, documents) -> None:
    """Apply the drag & drop order communicated via ?nt_order=id1,id2,..."""
    del session
    raw = st.query_params.get("nt_order")
    if not raw:
        return
    try:
        new_ids = [int(x) for x in str(raw).split(",")]
    except ValueError:
        return
    existing = [doc.id for doc in documents]
    if sorted(new_ids) == sorted(existing) and len(new_ids) == len(existing):
        with contextlib.suppress(Exception):
            container.document_service.reorder(project_id, new_ids)
    with contextlib.suppress(Exception):
        del st.query_params["nt_order"]
    st.rerun()


def _render_documents(container, session, project_id, documents) -> None:
    """Documents table: drag & drop order + multi-select delete (9.4-9.8)."""
    language = session.language
    t = lambda key: translate(key, language)  # noqa: E731

    if "selected_docs" not in st.session_state:
        st.session_state.selected_docs = set()

    locked = project_locked(container, project_id)

    # select-all + delete-selected bar
    bar_cols = st.columns([1, 3, 1])
    all_checked = len(st.session_state.selected_docs) == len(documents) and bool(documents)
    select_all = bar_cols[0].checkbox(t("doc.select_all"), value=all_checked, key="select_all_docs")
    if select_all and not all_checked:
        st.session_state.selected_docs = {doc.id for doc in documents}
        st.rerun()
    elif not select_all and all_checked:
        st.session_state.selected_docs = set()
        st.rerun()
    if st.session_state.selected_docs and bar_cols[2].button(
        f"🗑 {t('doc.delete')} ({len(st.session_state.selected_docs)})",
        key="delete_selected_btn",
    ):
        _delete_selected(container, project_id, tuple(st.session_state.selected_docs))

    # draggable table
    from noveltrad.ui.dnd import document_table

    document_table(
        documents,
        theme=session.theme,
        locked=locked,
        t=t,
    )

    # per-row selection below the table
    st.caption(t("doc.select_hint"))
    row_cols = st.columns(4)
    for index, doc in enumerate(documents):
        col = row_cols[index % 4]
        checked = col.checkbox(
            doc.display_name,
            value=doc.id in st.session_state.selected_docs,
            key=f"sel_{doc.id}",
        )
        if checked:
            st.session_state.selected_docs.add(doc.id)
        else:
            st.session_state.selected_docs.discard(doc.id)


def _delete_selected(container, project_id, document_ids: tuple) -> None:
    import contextlib

    document_service = container.document_service
    for document_id in document_ids:
        with contextlib.suppress(Exception):
            document_service.delete(document_id, None)
    st.session_state.selected_docs = set()
    st.rerun()


def project_locked(container, project_id) -> bool:
    """True when the project is running/paused (reorder disabled, RM-007)."""
    try:
        project = container.project_service.get(project_id)
        return project.status in (ProjectStatus.RUNNING, ProjectStatus.PAUSED)
    except Exception:  # noqa: BLE001
        return True

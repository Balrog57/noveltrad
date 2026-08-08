"""Projects view (SDD 13.4)."""

from __future__ import annotations

import streamlit as st

from noveltrad.core.contracts import LanguageCode
from noveltrad.core.languages import LANGUAGES, language_label
from noveltrad.ui.i18n import translate


def render(container, session) -> None:
    language = session.language
    t = lambda key: translate(key, language)  # noqa: E731
    st.title(t("app.title"))

    project_service = container.project_service
    projects = project_service.list()

    with st.expander(t("project.create"), expanded=not projects):
        name = st.text_input(t("project.name"), key="new_project_name")
        target_options = [
            (e.code, f"{language_label(e.code, language)} ({e.code})") for e in LANGUAGES
        ]
        target_label = st.selectbox(
            t("project.target"),
            [label for _, label in target_options],
            key="new_project_target",
        )
        target_code = next(c for c, label in target_options if label == target_label)
        if st.button(
            t("project.create_btn"),
            key="create_project_btn",
            disabled=not name.strip(),
            help=t("project.name_req") if not name.strip() else None,
        ):
            try:
                project = project_service.create(name, LanguageCode(target_code))
                session.current_project_id = project.id
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    search = st.text_input(t("project.search"), key="project_search")
    filtered = [p for p in projects if not search or search.lower() in p.name.lower()]

    for project in filtered:
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            cols[0].markdown(f"**{project.name}** — {project.status.value}")
            cols[1].markdown(f"_{t('project.language')}: {project.source_language or '?'}_")
            docs = container.document_service.list(project.id)
            cols[2].markdown(f"📄 {len(docs)}")
            if cols[3].button(t("project.open"), key=f"open_{project.id}"):
                session.current_project_id = project.id
                st.rerun()

    if not filtered and projects:
        st.info(t("project.search") + ": 0")

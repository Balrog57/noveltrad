"""UI router (SDD 13.3-13.16). Auth gate then view dispatch."""

from __future__ import annotations

import streamlit as st

from noveltrad.ui.i18n import translate
from noveltrad.ui.session import SessionState
from noveltrad.ui.theme import apply_theme


class Router:
    def __init__(self, container) -> None:
        self._container = container

    def render(self) -> None:
        session = self._get_session()
        self._sync_settings(session)
        apply_theme(session.theme)

        if not self._authenticate(session):
            return

        language = session.language
        t = lambda key: translate(key, language)  # noqa: E731
        with st.sidebar:
            st.title(t("app.title"))
            page = st.radio(
                "Navigation",
                [t("nav.projects"), t("nav.settings"), t("nav.logs"), t("nav.about")],
                key="nav",
            )

        if page == t("nav.projects"):
            if session.current_project_id is not None:
                from noveltrad.ui.views.project import render as render_project

                render_project(self._container, session)
            else:
                from noveltrad.ui.views.projects import render as render_projects

                render_projects(self._container, session)
        elif page == t("nav.settings"):
            from noveltrad.ui.views.settings import render as render_settings

            render_settings(self._container, session)
        elif page == t("nav.logs"):
            from noveltrad.ui.views.logs import render as render_logs

            render_logs(self._container, session)
        else:
            from noveltrad.ui.views.about import render as render_about

            render_about(self._container, session)

        for message_type, text in session.drain_messages():
            getattr(st, message_type, st.info)(text)

    # -- helpers ----------------------------------------------------------

    def _get_session(self) -> SessionState:
        if "session" not in st.session_state:
            st.session_state.session = SessionState()
        return st.session_state.session

    def _sync_settings(self, session: SessionState) -> None:
        try:
            view = self._container.settings_service.get_masked()
            session.language = view.ui_language
            session.theme = view.theme
        except Exception:  # noqa: BLE001
            pass

    def _authenticate(self, session: SessionState) -> bool:
        if session.authenticated:
            return True
        t = lambda key: translate(key, session.language)  # noqa: E731
        st.title(t("auth.title"))
        password = st.text_input(t("auth.password"), type="password", key="password_input")
        if st.button(t("auth.login"), key="login_btn"):
            try:
                if self._container.auth.authenticate(password):
                    session.authenticated = True
                    st.rerun()
                else:
                    st.error(t("auth.error"))
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
        return False

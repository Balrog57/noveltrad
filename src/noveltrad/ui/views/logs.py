"""Logs view (SDD 13.7, 16.12)."""

from __future__ import annotations

import streamlit as st

from noveltrad.core.contracts import LogLevel
from noveltrad.ui.i18n import translate


def render(container, session) -> None:
    language = session.language
    t = lambda key: translate(key, language)  # noqa: E731
    st.title(t("logs.title"))

    level = st.selectbox(
        t("logs.level"),
        [None, "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        format_func=lambda v: v or "ALL",
    )
    entries = container.logs.query(
        level=LogLevel(level) if level else None,
        limit=200,
    )
    for entry in entries:
        st.markdown(
            f"`{entry.created_at.strftime('%H:%M:%S')}` **{entry.level.value}** "
            f"`{entry.event}` — {entry.safe_message}"
        )

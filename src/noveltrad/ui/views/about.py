"""About view (SDD 13.11): AGPL-3.0-only, no warranty, version, commit,
link to https://github.com/Balrog57/noveltrad/tree/<source_commit>."""

from __future__ import annotations

import streamlit as st

from noveltrad.core.build_info import __version__, source_commit
from noveltrad.ui.i18n import translate

_REPO = "https://github.com/Balrog57/noveltrad"


def render(container, session) -> None:
    del container
    language = session.language
    t = lambda key: translate(key, language)  # noqa: E731
    st.title(t("about.title"))
    st.markdown(f"**{t('about.license')}**: GNU Affero General Public License v3.0 only")
    st.markdown(f"**{t('about.version')}**: {__version__}")
    commit = source_commit()
    st.markdown(f"**{t('about.commit')}**: `{commit}`")
    if commit:
        st.markdown(f"[{t('about.source')}]({_REPO}/tree/{commit})")
    else:
        st.markdown(f"[{t('about.source')}]({_REPO})")

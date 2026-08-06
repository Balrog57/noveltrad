"""Settings view (SDD 13.6, 14)."""

from __future__ import annotations

import streamlit as st

from noveltrad.core.contracts import ProviderName, SettingsUpdate
from noveltrad.ui.i18n import translate

_PROVIDERS = {
    "Ollama": "ollama",
    "LM Studio": "lm_studio",
    "API OpenAI-compatible": "openai_compatible",
}


def render(container, session) -> None:
    language = session.language
    t = lambda key: translate(key, language)  # noqa: E731
    st.title(t("settings.title"))

    settings_service = container.settings_service
    current = settings_service.get_masked()

    themes = ["light", "dark", "sepia"]
    ui_language = st.radio(
        t("settings.ui_language"), ["fr", "en"], index=0 if current.ui_language == "fr" else 1
    )
    theme = st.radio(t("settings.theme"), themes, index=themes.index(current.theme))
    sound = st.checkbox(t("settings.sound"), value=current.completion_sound_enabled)

    provider_names = list(_PROVIDERS.keys())
    current_provider = next(
        (name for name, code in _PROVIDERS.items() if code == str(current.provider)),
        provider_names[0],
    )
    provider_label = st.selectbox(
        t("settings.provider"), provider_names, index=provider_names.index(current_provider)
    )
    base_url = st.text_input(t("settings.url"), value=current.base_url or "")
    placeholder = "••••••••" if current.api_key_configured else ""
    api_key = st.text_input(
        t("settings.api_key"), value="", type="password", placeholder=placeholder
    )
    model = st.text_input(t("settings.model"), value=current.model or "")
    window = st.number_input(
        t("settings.window"),
        min_value=2048,
        max_value=1048576,
        value=current.context_window_tokens or 8192,
        step=1024,
    )
    temperature = st.slider(t("settings.temperature"), 0.0, 2.0, current.temperature, 0.1)
    max_output = st.number_input(
        t("settings.max_output"), min_value=512, value=current.max_output_tokens or 2048, step=256
    )
    seed_value = current.seed if current.seed is not None else 0
    seed = st.number_input(t("settings.seed"), value=seed_value, step=1)

    api_key_action = "KEEP"
    if api_key:
        api_key_action = "REPLACE"

    if st.button(t("settings.test"), key="test_conn_btn"):
        with st.spinner("..."):
            report = settings_service.validate_configuration()
            if report.valid:
                st.success("OK")
            else:
                for message in report.safe_messages:
                    st.error(message)

    if st.button(t("settings.models"), key="list_models_btn"):
        try:
            models = settings_service.list_models()
            st.write(", ".join(models) if models else "—")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    if st.button(t("settings.save"), key="save_settings_btn"):
        try:
            settings_service.update(
                SettingsUpdate(
                    ui_language=ui_language,
                    theme=theme,
                    completion_sound_enabled=sound,
                    provider=ProviderName(_PROVIDERS[provider_label]),
                    base_url=base_url or None,
                    model=model or None,
                    context_window_tokens=int(window),
                    temperature=float(temperature),
                    max_output_tokens=int(max_output),
                    seed=int(seed) if seed else None,
                    api_key_action=api_key_action,
                    api_key_value=api_key or None,
                )
            )
            session.language = ui_language
            session.theme = theme
            st.success(t("settings.save"))
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

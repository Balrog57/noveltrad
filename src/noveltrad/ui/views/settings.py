"""Settings view (SDD 13.6, 14).

Each provider exposes URL, optional API key (enabled explicitly) and
auto-detection of installed models using the current form values. The
connection test also uses the form values, without saving anything.
"""

from __future__ import annotations

import streamlit as st

from noveltrad.core.contracts import ProviderName, SettingsUpdate
from noveltrad.ui.i18n import translate

# Providers that require an API key to work at all
_REQUIRE_KEY = frozenset({"openai_compatible"})
# Providers with local auto-detection of installed models
_AUTO_DETECT = frozenset({"ollama", "lm_studio"})

# Preset provider labels mapped to (adapter code, default URL)
_PRESETS = {
    "Ollama": ("ollama", "http://host.docker.internal:11434"),
    "LM Studio": ("lm_studio", "http://host.docker.internal:1234/v1"),
    "OpenAI (ChatGPT)": ("openai_compatible", "https://api.openai.com/v1"),
    "Google Gemini": ("openai_compatible", "https://generativelanguage.googleapis.com/v1beta/openai"),
    "DeepSeek": ("openai_compatible", "https://api.deepseek.com/v1"),
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

    preset_names = list(_PRESETS.keys())
    current_label = next(
        (name for name, (code, _url) in _PRESETS.items()
         if code == str(current.provider)
         and (current.base_url or "") == (_url if _url else "")),
        None,
    )
    if current_label is None:
        # fall back on matching the adapter code alone
        current_label = next(
            (name for name, (code, _url) in _PRESETS.items()
             if code == str(current.provider)),
            preset_names[0],
        )
    provider_label = st.selectbox(
        t("settings.provider"), preset_names, index=preset_names.index(current_label)
    )
    provider_code, preset_url = _PRESETS[provider_label]

    # -- provider section -------------------------------------------------
    st.subheader(provider_label)
    base_url = st.text_input(
        t("settings.url"),
        value=current.base_url or preset_url,
        key="provider_url",
    )

    api_key_enabled = st.checkbox(
        t("settings.api_key"),
        value=current.api_key_configured or provider_code in _REQUIRE_KEY,
        help=t("settings.api_key") + " (optional)",
    )
    api_key = ""
    if api_key_enabled:
        placeholder = "••••••••" if current.api_key_configured else ""
        api_key = st.text_input(
            t("settings.api_key"), value="", type="password", placeholder=placeholder
        )

    model = st.text_input(t("settings.model"), value=current.model or "")

    if provider_code in _AUTO_DETECT:
        if st.button(t("settings.models"), key="list_models_btn"):
            with st.spinner("..."):
                models = settings_service.list_models_for(
                    ProviderName(provider_code),
                    base_url,
                    api_key if api_key else None,
                    model,
                )
            if models:
                st.write(", ".join(models))
            else:
                st.warning("—")
    else:
        st.caption(t("settings.models") + ": manual")

    # -- advanced section -------------------------------------------------
    window = current.context_window_tokens or 8192
    temperature = current.temperature
    max_output = current.max_output_tokens or 2048
    seed_value = current.seed if current.seed is not None else 0
    with st.expander(t("settings.window")):
        window = st.number_input(
            t("settings.window"),
            min_value=2048,
            max_value=1048576,
            value=int(window),
            step=1024,
        )
        temperature = st.slider(t("settings.temperature"), 0.0, 2.0, temperature, 0.1)
        max_output = st.number_input(
            t("settings.max_output"), min_value=512, value=int(max_output), step=256
        )
        seed = st.number_input(t("settings.seed"), value=int(seed_value), step=1)

    api_key_action = "KEEP"
    if api_key:
        api_key_action = "REPLACE"
    elif api_key_enabled and not current.api_key_configured and not api_key:
        api_key_action = "DELETE"

    col_test, col_save = st.columns(2)
    if col_test.button(t("settings.test"), key="test_conn_btn"):
        with st.spinner("..."):
            report = settings_service.validate_configuration_for(
                ProviderName(provider_code),
                base_url,
                api_key or None,
                model,
            )
        if report.valid:
            st.success("OK")
        else:
            for message in report.safe_messages:
                st.error(message)

    if col_save.button(t("settings.save"), key="save_settings_btn"):
        try:
            settings_service.update(
                SettingsUpdate(
                    ui_language=ui_language,
                    theme=theme,
                    completion_sound_enabled=sound,
                    provider=ProviderName(provider_code),
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

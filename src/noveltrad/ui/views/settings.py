"""Settings view (SDD 13.6, 14).

Seven provider presets: Ollama and LM Studio (local, model auto-detection),
OpenAI/ChatGPT, Google Gemini, DeepSeek, Grok (xAI) and Claude (Anthropic)
(cloud, model list preloaded + optional auto-detection), plus a fully
manual OpenAI-compatible entry. Cloud providers only need the API key.
"""

from __future__ import annotations

import streamlit as st

from noveltrad.core.contracts import ProviderName, SettingsUpdate
from noveltrad.ui.i18n import translate

# Preset label -> (adapter code, default URL, requires key, known models)
_PRESETS: dict[str, tuple[str, str, bool, tuple[str, ...]]] = {
    "Ollama": (
        "ollama",
        "http://host.docker.internal:11434",
        False,
        (),
    ),
    "LM Studio": (
        "lm_studio",
        "http://host.docker.internal:1234/v1",
        False,
        (),
    ),
    "OpenAI-compatible (personnalisé)": (
        "openai_compatible",
        "http://localhost:8000/v1",
        False,
        (),
    ),
    "OpenAI (ChatGPT)": (
        "openai_compatible",
        "https://api.openai.com/v1",
        True,
        (
            "gpt-5.6-sol",
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "gpt-5",
            "gpt-5-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
        ),
    ),
    "Google Gemini": (
        "openai_compatible",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        True,
        (
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.1-pro",
            "gemini-3.1-flash-lite",
            "gemini-3-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ),
    ),
    "DeepSeek": (
        "openai_compatible",
        "https://api.deepseek.com/v1",
        True,
        ("deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"),
    ),
    "Grok (xAI)": (
        "openai_compatible",
        "https://api.x.ai/v1",
        True,
        (
            "grok-4.5",
            "grok-4.3",
            "grok-4.20-0309-reasoning",
            "grok-4.20-0309-non-reasoning",
            "grok-3",
            "grok-3-mini",
            "grok-2",
            "grok-2-latest",
        ),
    ),
    "Claude (Anthropic)": (
        "anthropic",
        "https://api.anthropic.com",
        True,
        (
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ),
    ),
}

# Providers that support model auto-detection via /models
_AUTO_DETECT = frozenset({"ollama", "lm_studio", "openai_compatible"})


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
        (
            name
            for name, (code, _url, _key, _models) in _PRESETS.items()
            if code == str(current.provider) and (current.base_url or "") == (_url if _url else "")
        ),
        None,
    )
    if current_label is None:
        current_label = next(
            (
                name
                for name, (code, _url, _key, _models) in _PRESETS.items()
                if code == str(current.provider)
            ),
            preset_names[0],
        )
    provider_label = st.selectbox(
        t("settings.provider"), preset_names, index=preset_names.index(current_label)
    )
    provider_code, preset_url, requires_key, known_models = _PRESETS[provider_label]

    # -- provider section -------------------------------------------------
    st.subheader(provider_label)

    # The URL field keeps a distinct session key per preset so switching
    # presets shows the preset default instead of the previous value.
    url_key = f"provider_url_{provider_label}"
    url_value = st.session_state.get(url_key)
    if url_value is None:
        url_value = current.base_url or preset_url
    base_url = st.text_input(
        t("settings.url"),
        value=url_value,
        key=url_key,
    )

    api_key_enabled = st.checkbox(
        t("settings.api_key"),
        value=current.api_key_configured or requires_key,
        help=t("settings.api_key") + (" (required)" if requires_key else " (optional)"),
    )
    api_key = ""
    if api_key_enabled:
        placeholder = "••••••••" if current.api_key_configured else ""
        api_key = st.text_input(
            t("settings.api_key"), value="", type="password", placeholder=placeholder
        )

    # -- model selection ---------------------------------------------------
    if "detected_models" not in st.session_state:
        st.session_state.detected_models = None

    if provider_code in _AUTO_DETECT:
        detect_col, spacer = st.columns([1, 3])
        if detect_col.button(t("settings.models"), key="list_models_btn"):
            with st.spinner("..."):
                models = settings_service.list_models_for(
                    ProviderName(provider_code),
                    base_url,
                    api_key if api_key else None,
                    current.model,
                )
            if models:
                st.session_state.detected_models = models
            else:
                st.warning("—")

    model_options = st.session_state.detected_models or known_models
    if model_options:
        current_model = current.model or model_options[0]
        model_index = model_options.index(current_model) if current_model in model_options else 0
        model = st.selectbox(
            t("settings.model"), list(model_options), index=model_index, key="model_select"
        )
    else:
        model = st.text_input(t("settings.model"), value=current.model or "")

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
            st.session_state.detected_models = None
            st.success(t("settings.save"))
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

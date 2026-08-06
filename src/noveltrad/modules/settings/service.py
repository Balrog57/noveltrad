"""SettingsService (SDD 5.8, 14).

Global settings: UI language, theme, sound flag, provider, base URL,
encrypted API key, model, window, temperature, max output tokens, seed.
Refuses any mutation while a translation is active (RM-012). Keys are
never shown in clear text; an empty field means "keep existing" and a
distinct explicit action deletes the key.
"""

from __future__ import annotations

import sqlite3

from noveltrad.core.contracts import (
    ProviderName,
    SettingsUpdate,
    SettingsView,
    ValidationReport,
)
from noveltrad.core.exceptions import LockedError
from noveltrad.core.logging import LogContext, LogService, new_correlation_id
from noveltrad.core.security import decrypt_secret, encrypt_secret
from noveltrad.core.transactions import UnitOfWork

from .repository import SettingsRepository

_KEY_UI_LANGUAGE = "ui_language"
_KEY_THEME = "theme"
_KEY_COMPLETION_SOUND = "completion_sound_enabled"
_KEY_PROVIDER = "provider"
_KEY_BASE_URL = "base_url"
_KEY_API_KEY = "api_key"
_KEY_MODEL = "model"
_KEY_CONTEXT_WINDOW = "context_window_tokens"
_KEY_TEMPERATURE = "temperature"
_KEY_MAX_OUTPUT = "max_output_tokens"
_KEY_SEED = "seed"

_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_MAX_OUTPUT_FACTOR = 0.35


class SettingsService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        repository: SettingsRepository,
        logs: LogService,
        encryption_key: bytes,
        factory=None,
    ) -> None:
        self._conn = conn
        self._repo = repository
        self._logs = logs
        self._key = encryption_key
        self._factory = factory

    # -- queries ----------------------------------------------------------

    def get_masked(self) -> SettingsView:
        def value(key: str) -> str | None:
            raw, _ = self._repo.get(key)
            return raw

        provider_raw = value(_KEY_PROVIDER)
        context_raw = value(_KEY_CONTEXT_WINDOW)
        max_raw = value(_KEY_MAX_OUTPUT)
        seed_raw = value(_KEY_SEED)
        temperature_raw = value(_KEY_TEMPERATURE)
        api_key, api_key_secret = self._repo.get(_KEY_API_KEY)
        return SettingsView(
            ui_language=_parse_language(value(_KEY_UI_LANGUAGE)),
            theme=_parse_theme(value(_KEY_THEME)),
            completion_sound_enabled=value(_KEY_COMPLETION_SOUND) != "false",
            provider=ProviderName(provider_raw) if provider_raw else None,
            base_url=value(_KEY_BASE_URL),
            api_key_configured=bool(api_key and api_key_secret),
            model=value(_KEY_MODEL),
            context_window_tokens=_parse_int(context_raw),
            temperature=_parse_float(temperature_raw, _DEFAULT_TEMPERATURE),
            max_output_tokens=_parse_int(max_raw),
            seed=_parse_int(seed_raw),
        )

    async def validate_configuration(self) -> ValidationReport:
        settings = self.get_masked()
        if settings.provider is None or not settings.base_url or not settings.model:
            return ValidationReport(
                False,
                ("INCOMPLETE_CONFIG",),
                ("provider, base URL and model are required",),
            )
        if self._factory is None:
            return ValidationReport(False, ("NO_FACTORY",), ("provider factory missing",))
        if settings.provider == ProviderName.OPENAI_COMPATIBLE:
            if not settings.api_key_configured:
                return ValidationReport(
                    False, ("API_KEY_MISSING",), ("API key required for this provider",)
                )
            self._factory.set_api_key(self._decrypt_api_key())
        try:
            provider = self._factory.create(settings)
            try:
                return await provider.validate_configuration(settings_to_snapshot(settings))
            finally:
                await provider.close()
        except Exception as exc:  # noqa: BLE001
            return ValidationReport(
                False, ("PROVIDER_ERROR",), (f"configuration invalid: {exc}",)
            )

    async def list_models(self) -> tuple[str, ...]:
        settings = self.get_masked()
        if settings.provider is None:
            return ()
        if self._factory is None:
            return ()
        if settings.provider == ProviderName.OPENAI_COMPATIBLE:
            self._factory.set_api_key(self._decrypt_api_key())
        provider = self._factory.create(settings)
        try:
            return await provider.list_models()
        finally:
            await provider.close()

    # -- mutation ---------------------------------------------------------

    def update(self, values: SettingsUpdate) -> SettingsView:
        self._ensure_unlocked()
        with UnitOfWork(self._conn):
            self._repo.set(_KEY_UI_LANGUAGE, values.ui_language)
            self._repo.set(_KEY_THEME, values.theme)
            self._repo.set(
                _KEY_COMPLETION_SOUND, "true" if values.completion_sound_enabled else "false"
            )
            provider_value = (
                values.provider.value
                if hasattr(values.provider, "value")
                else values.provider
            )
            self._repo.set(_KEY_PROVIDER, provider_value)
            self._repo.set(_KEY_BASE_URL, values.base_url)
            self._repo.set(_KEY_MODEL, values.model)
            if values.context_window_tokens is not None:
                self._repo.set(_KEY_CONTEXT_WINDOW, str(values.context_window_tokens))
            if values.temperature is not None:
                self._repo.set(_KEY_TEMPERATURE, str(values.temperature))
            if values.max_output_tokens is not None:
                self._repo.set(_KEY_MAX_OUTPUT, str(values.max_output_tokens))
            if values.seed is not None:
                self._repo.set(_KEY_SEED, str(values.seed))
            if values.api_key_action == "REPLACE" and values.api_key_value:
                envelope = encrypt_secret(self._key, "api_key", values.api_key_value)
                self._repo.set(_KEY_API_KEY, envelope, is_secret=True)
            elif values.api_key_action == "DELETE":
                self._repo.delete(_KEY_API_KEY)
            self._logs.record(
                "INFO",
                "settings.update",
                "settings updated",
                LogContext(correlation_id=new_correlation_id()),
            )
        return self.get_masked()

    # -- helpers ----------------------------------------------------------

    def _decrypt_api_key(self) -> str | None:
        raw, is_secret = self._repo.get(_KEY_API_KEY)
        if not raw or not is_secret:
            return None
        return decrypt_secret(self._key, "api_key", raw)

    def _ensure_unlocked(self) -> None:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM jobs WHERE state IN ('Running','Retrying')"
        ).fetchone()
        if row["c"] > 0:
            raise LockedError("settings cannot change during an active translation")


def _parse_language(value: str | None) -> str:
    return value if value in ("fr", "en") else "fr"


def _parse_theme(value: str | None) -> str:
    return value if value in ("light", "dark", "sepia") else "light"


def _parse_int(value: str | None) -> int | None:
    return int(value) if value else None


def _parse_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def settings_to_snapshot(settings: SettingsView):
    """Build a PipelineSnapshot from settings (used for validation)."""
    from noveltrad.core.contracts import PipelineSnapshot

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
        snapshot_hash="",
    )

"""Provider factory (SDD 14.14). Maps the global configuration to exactly
one of the three adapters."""

from __future__ import annotations

from noveltrad.core.contracts import ProviderName, SettingsView
from noveltrad.core.exceptions import ValidationError

from .lm_studio import LMStudioProvider
from .ollama import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider


class ProviderFactory:
    def __init__(self) -> None:
        self._api_key: str | None = None

    def set_api_key(self, api_key: str | None) -> None:
        self._api_key = api_key

    def create(self, settings: SettingsView):
        if settings.provider is None:
            raise ValidationError("no AI provider configured")
        if settings.provider == ProviderName.OLLAMA:
            return OllamaProvider()
        if settings.provider == ProviderName.LM_STUDIO:
            return LMStudioProvider()
        if settings.provider == ProviderName.OPENAI_COMPATIBLE:
            provider = OpenAICompatibleProvider()
            provider.set_api_key(self._api_key)
            return provider
        raise ValidationError(f"unknown provider: {settings.provider}")

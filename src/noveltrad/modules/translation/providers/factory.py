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

    def create_from_settings(self, settings: SettingsView):
        """Build a provider from SettingsView directly (used by container)."""
        base_url = settings.base_url or ""
        if settings.provider == ProviderName.OLLAMA:
            return OllamaProvider(base_url=base_url)
        if settings.provider == ProviderName.LM_STUDIO:
            provider = LMStudioProvider()
            if base_url:
                provider.set_base_url(base_url)
            return provider
        if settings.provider == ProviderName.OPENAI_COMPATIBLE:
            provider = OpenAICompatibleProvider()
            provider.set_api_key(self._api_key)
            if base_url:
                provider.set_base_url(base_url)
            return provider
        raise ValidationError(f"unknown provider: {settings.provider}")

    def create(self, settings: SettingsView):
        return self.create_from_settings(settings)

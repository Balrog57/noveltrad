"""Nexum Router provider using its OpenAI-compatible endpoint."""

from typing import Callable, List, Optional, Union
from src.config import OLLAMA_NUM_CTX
from .openai import OpenAICompatibleProvider


class NexumProvider(OpenAICompatibleProvider):
    DEFAULT_API_ENDPOINT = "https://dialagram.me/router/v1"
    FALLBACK_MODELS = ["qwen-3.7-max", "deepseek-v4", "xiaomi-mimo-2.5"]

    def __init__(
        self,
        api_key: Union[str, List[str]],
        model: str = FALLBACK_MODELS[0],
        api_endpoint: Optional[str] = None,
        context_window: Optional[int] = None,
        log_callback: Optional[Callable] = None,
    ):
        super().__init__(
            api_endpoint or self.DEFAULT_API_ENDPOINT,
            model,
            api_key=api_key,
            context_window=context_window or OLLAMA_NUM_CTX,
            log_callback=log_callback,
            provider_name="nexum",
        )

    async def get_available_models(self) -> list:
        try:
            base = self.api_endpoint.rsplit("/chat/completions", 1)[0]
            response = await (await self._get_client()).get(f"{base}/models", headers={"Authorization": f"Bearer {self.api_key}"}, timeout=15)
            response.raise_for_status()
            models = response.json().get("data", [])
            if models:
                return [{"id": m.get("id", ""), "name": m.get("id", "")} for m in models if m.get("id")]
        except Exception:
            pass
        return [{"id": m, "name": m} for m in self.FALLBACK_MODELS]

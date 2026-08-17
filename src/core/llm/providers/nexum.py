"""Nexum Router provider using its OpenAI-compatible endpoint."""

from typing import Callable, List, Optional, Union
from src.config import OLLAMA_NUM_CTX, REQUEST_TIMEOUT
from .openai import OpenAICompatibleProvider


class NexumProvider(OpenAICompatibleProvider):
    DEFAULT_API_ENDPOINT = "https://dialagram.me/router/v1"
    FALLBACK_MODELS = ["qwen-3.7-max", "deepseek-v4", "xiaomi-mimo-2.5"]

    # Dialagram routinely drops completions (empty 200, 0 tokens, 5xx). Give
    # those glitches more retries than the global default.
    MAX_GENERATE_ATTEMPTS = 5

    # Reasoning models routed through Dialagram (deepseek-v4) routinely spend
    # 6-10k completion tokens on chain-of-thought before writing the answer.
    # A default cap low enough to truncate that would return an empty
    # ``content``, so reserve a large completion budget for the transcript.
    DEFAULT_MAX_OUTPUT_TOKENS = 32768

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

    async def generate(self, prompt: str, timeout: int = REQUEST_TIMEOUT,
                      system_prompt: Optional[str] = None,
                      **generation_options):
        """Generate with a generous completion budget by default.

        ``max_tokens`` can still be overridden per call via ``generation_options``.
        Reasoning models (deepseek-v4) otherwise spend the whole budget on
        chain-of-thought and return empty ``content`` with finish_reason=length.
        """
        generation_options.setdefault("max_tokens", self.DEFAULT_MAX_OUTPUT_TOKENS)
        # Dialagram forwards this to DeepSeek V4, which thinks unless given
        # the struct ``{"type": "disabled"}``. A boolean ``false`` is a 400
        # (``expected struct ThinkingOptions``). llama.cpp-style
        # ``enable_thinking`` is not part of that schema — omit it.
        if "deepseek" in (self.model or "").lower():
            generation_options.setdefault("thinking", {"type": "disabled"})
        return await super().generate(
            prompt, timeout=timeout, system_prompt=system_prompt, **generation_options
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

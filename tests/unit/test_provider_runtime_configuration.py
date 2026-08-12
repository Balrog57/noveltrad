import pytest

from src.core import llm_client as llm_client_module
from src.core.llm import factory
from src.core.llm.providers.anthropic import AnthropicProvider
from src.core.llm.providers.openai import OpenAICompatibleProvider
from src.api.blueprints import translation_routes


@pytest.mark.parametrize(
    ("provider", "key_argument"),
    [
        ("anthropic", "anthropic_api_key"),
        ("xai", "xai_api_key"),
        ("nexum", "nexum_api_key"),
    ],
)
def test_create_llm_client_passes_runtime_provider_configuration(
    monkeypatch, provider, key_argument
):
    captured = {}

    def fake_create(provider_type, **kwargs):
        captured["provider_type"] = provider_type
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(llm_client_module, "create_llm_provider", fake_create)
    client = llm_client_module.create_llm_client(
        provider,
        None,
        "https://configured.example/v1",
        "test-model",
        **{key_argument: "secret"},
        context_window=8192,
        log_callback=lambda *_: None,
    )

    client._get_provider()

    assert captured["provider_type"] == provider
    assert captured["api_endpoint"] == "https://configured.example/v1"
    assert captured["context_window"] == 8192
    assert captured["log_callback"] is not None


@pytest.mark.parametrize("provider", ["anthropic", "xai", "nexum"])
def test_provider_factory_preserves_runtime_configuration(monkeypatch, provider):
    captured = {}

    class CaptureProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(factory, {
        "anthropic": "AnthropicProvider",
        "xai": "XAIProvider",
        "nexum": "NexumProvider",
    }[provider], CaptureProvider)

    factory.create_llm_provider(
        provider,
        api_key="secret",
        model="test-model",
        api_endpoint="https://configured.example/v1",
        context_window=8192,
        log_callback=lambda *_: None,
    )

    assert captured == {
        "api_key": "secret",
        "model": "test-model",
        "api_endpoint": "https://configured.example/v1",
        "context_window": 8192,
        "log_callback": captured["log_callback"],
    }


def test_new_cloud_provider_endpoints_are_runtime_overrides():
    assert {"anthropic", "xai", "nexum"}.issubset(
        set(translation_routes._ENDPOINT_CONSUMING_PROVIDERS)
    )
    assert translation_routes._server_default_endpoint("nexum")
    assert translation_routes._is_endpoint_override(
        {"llm_provider": "nexum"}, "https://custom.example/v1"
    )


@pytest.mark.asyncio
async def test_anthropic_marks_max_token_response_as_truncated(monkeypatch):
    provider = AnthropicProvider(
        api_key="secret",
        model="test-model",
        max_output_tokens=777,
    )

    class FakeResponse:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "content": [{"type": "text", "text": "partial"}],
                "stop_reason": "max_tokens",
                "usage": {"input_tokens": 2, "output_tokens": 777},
            }

    class FakeClient:
        async def post(self, url, **kwargs):
            self.url = url
            self.request = kwargs
            return FakeResponse()

    client = FakeClient()

    async def get_client():
        return client

    monkeypatch.setattr(provider, "_get_client", get_client)
    response = await provider.generate("prompt")

    assert response.content == "partial"
    assert response.was_truncated is True
    assert client.request["json"]["max_tokens"] == 777


@pytest.mark.asyncio
async def test_openai_compatible_accepts_generation_controls(monkeypatch):
    provider = OpenAICompatibleProvider(
        api_endpoint="https://example.test/v1",
        model="test-model",
        api_key="secret",
    )

    class FakeResponse:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            }

    class FakeClient:
        async def post(self, url, **kwargs):
            self.url = url
            self.request = kwargs
            return FakeResponse()

    client = FakeClient()

    async def get_client():
        return client

    monkeypatch.setattr(provider, "_get_client", get_client)
    response = await provider.generate(
        "prompt", temperature=0.2, top_p=0.8, max_tokens=123
    )

    assert response.content == "ok"
    assert client.request["json"]["temperature"] == 0.2
    assert client.request["json"]["top_p"] == 0.8
    assert client.request["json"]["max_tokens"] == 123


@pytest.mark.asyncio
async def test_llm_client_forwards_generation_controls(monkeypatch):
    captured = {}

    class FakeProvider:
        async def generate(self, prompt, timeout=30, system_prompt=None, **options):
            captured.update(options)
            return None

    monkeypatch.setattr(
        llm_client_module,
        "create_llm_provider",
        lambda *_args, **_kwargs: FakeProvider(),
    )
    client = llm_client_module.LLMClient(
        provider_type="xai",
        api_endpoint="https://example.test/v1",
        model="test-model",
    )
    await client.generate("prompt", temperature=0.1, top_p=0.9, max_tokens=99)
    assert captured == {"temperature": 0.1, "top_p": 0.9, "max_tokens": 99}

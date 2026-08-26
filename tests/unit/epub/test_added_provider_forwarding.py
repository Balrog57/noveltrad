import pytest

from src.core.epub.translator import _create_llm_client, translate_epub_file


@pytest.mark.asyncio
async def test_epub_entrypoint_accepts_added_provider_credentials(tmp_path):
    """Regression: web jobs must not crash before opening an EPUB."""
    missing_epub = tmp_path / "missing.epub"

    result = await translate_epub_file(
        input_filepath=str(missing_epub),
        output_filepath=str(tmp_path / "output.epub"),
        anthropic_api_key="anthropic-secret",
        xai_api_key="xai-secret",
        opencode_api_key="opencode-secret",
        opencodego_api_key="opencodego-secret",
        ollamacloud_api_key="ollama-cloud-key",
    )

    assert result is None


@pytest.mark.parametrize(
    ("provider", "credential_name"),
    [
        ("anthropic", "anthropic_api_key"),
        ("xai", "xai_api_key"),
        ("opencode", "opencode_api_key"),
        ("opencodego", "opencodego_api_key"),
        ("ollamacloud", "ollamacloud_api_key"),
    ],
)
def test_epub_client_uses_added_provider_credential(provider, credential_name):
    credentials = {
        "anthropic_api_key": None,
        "xai_api_key": None,
        "opencode_api_key": None,
        "opencodego_api_key": None,
        "ollamacloud_api_key": None,
    }
    credentials[credential_name] = "provider-secret"

    client = _create_llm_client(
        llm_provider=provider,
        model_name="test-model",
        gemini_api_key=None,
        openai_api_key=None,
        openrouter_api_key=None,
        mistral_api_key=None,
        deepseek_api_key=None,
        poe_api_key=None,
        nim_api_key=None,
        cli_api_endpoint="https://example.invalid/v1",
        initial_context=4096,
        **credentials,
    )

    assert client.provider_type == provider
    assert client.provider_kwargs["api_key"] == "provider-secret"


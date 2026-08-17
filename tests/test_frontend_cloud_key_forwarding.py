"""Frontend job payloads must send UI-entered cloud API keys.

A key typed only in the form (not stored in .env) used to be dropped for
Anthropic / xAI / Nexum. Failed generate() calls then kept the source text.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCH = ROOT / "src" / "web" / "static" / "js" / "translation" / "batch-controller.js"
FORM = ROOT / "src" / "web" / "static" / "js" / "ui" / "form-manager.js"

CLOUD_KEY_FIELDS = (
    "anthropic_api_key",
    "xai_api_key",
    "nexum_api_key",
    "opencode_api_key",
    "opencodego_api_key",
)


def test_batch_controller_forwards_cloud_api_keys():
    source = BATCH.read_text(encoding="utf-8")
    for field in CLOUD_KEY_FIELDS:
        assert f"{field}:" in source, f"batch-controller missing {field}"
        assert "ApiKeyUtils.getValue" in source


def test_form_manager_forwards_cloud_api_keys():
    source = FORM.read_text(encoding="utf-8")
    for field in CLOUD_KEY_FIELDS:
        assert f"{field}:" in source, f"form-manager missing {field}"


def test_batch_controller_forwards_chunk_size():
    source = BATCH.read_text(encoding="utf-8")
    assert "max_tokens_per_chunk:" in source
    assert "maxTokensPerChunk" in source


def test_form_manager_forwards_chunk_size():
    source = FORM.read_text(encoding="utf-8")
    assert "max_tokens_per_chunk:" in source
    assert "maxTokensPerChunk" in source


def test_settings_dirty_tracks_nexum_and_chunk_size():
    settings = (ROOT / "src" / "web" / "static" / "js" / "core" / "settings-manager.js").read_text(
        encoding="utf-8"
    )
    for field_id in (
        "nexumApiKey",
        "anthropicApiKey",
        "xaiApiKey",
        "opencodeApiKey",
        "opencodegoApiKey",
        "maxTokensPerChunk",
    ):
        assert f"id: '{field_id}'" in settings

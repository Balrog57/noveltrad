"""Unit tests for SettingsService (SDD 14, RM-012)."""

from __future__ import annotations

import sqlite3

import pytest

from noveltrad.core.contracts import ProviderName, SettingsUpdate
from noveltrad.core.exceptions import LockedError
from noveltrad.core.logging import LogService
from noveltrad.core.security import derive_key
from noveltrad.modules.settings.repository import SettingsRepository
from noveltrad.modules.settings.service import SettingsService


@pytest.fixture
def settings_service(conn: sqlite3.Connection):
    logs = LogService(conn)
    repo = SettingsRepository(conn)
    key = derive_key("test-password-for-settings", b"\x01" * 16)
    return SettingsService(conn, repo, logs, key)


def _update(**overrides) -> SettingsUpdate:
    base = dict(
        ui_language="fr",
        theme="dark",
        completion_sound_enabled=True,
        provider="ollama",
        base_url="http://localhost:11434",
        model="qwen2.5",
        context_window_tokens=8192,
        temperature=0.2,
        max_output_tokens=2048,
        seed=None,
        api_key_action="KEEP",
        api_key_value=None,
    )
    base.update(overrides)
    return SettingsUpdate(**base)


def test_update_and_get_masked(settings_service: SettingsService):
    settings_service.update(_update())
    view = settings_service.get_masked()
    assert view.ui_language == "fr"
    assert view.theme == "dark"
    assert view.provider == ProviderName.OLLAMA
    assert view.model == "qwen2.5"
    assert view.context_window_tokens == 8192
    assert view.api_key_configured is False


def test_api_key_encrypted_at_rest(settings_service: SettingsService, conn: sqlite3.Connection):
    settings_service.update(_update(api_key_action="REPLACE", api_key_value="sk-secret-123"))
    row = conn.execute("SELECT value, is_secret FROM settings WHERE key='api_key'").fetchone()
    assert row[1] == 1
    assert "sk-secret-123" not in row[0]
    view = settings_service.get_masked()
    assert view.api_key_configured is True


def test_api_key_delete(settings_service: SettingsService, conn: sqlite3.Connection):
    settings_service.update(_update(api_key_action="REPLACE", api_key_value="sk-x"))
    settings_service.update(_update(api_key_action="DELETE"))
    row = conn.execute("SELECT value FROM settings WHERE key='api_key'").fetchone()
    assert row is None


def test_update_locked_during_translation(
    settings_service: SettingsService, conn: sqlite3.Connection
):
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO projects (name, target_language, status, created_at, updated_at) "
        "VALUES ('x', 'fr', 'Running', ?, ?)",
        (now, now),
    )
    conn.commit()
    conn.execute(
        "INSERT INTO documents (project_id, display_name, import_format, order_index, "
        "source_path, source_hash, status, updated_at) "
        "VALUES (1, 'd', 'txt', 0, 'p', 'h', 'Running', ?)",
        (now,),
    )
    conn.commit()
    conn.execute(
        "INSERT INTO jobs (document_id, state, provider, model, snapshot_json, "
        "snapshot_hash, queued_at) VALUES (1, 'Running', 'ollama', 'm', '{}', 'h', ?)",
        (now,),
    )
    conn.commit()
    with pytest.raises(LockedError):
        settings_service.update(_update())


def test_plaintext_secret_refused(conn: sqlite3.Connection):
    from noveltrad.core.exceptions import IntegrityError

    repo = SettingsRepository(conn)
    with pytest.raises(IntegrityError):
        repo.set("api_key", "plaintext", is_secret=True)

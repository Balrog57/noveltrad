"""Tests for the auto-update logic (CDC §5 packaging follow-up).

Network calls are mocked so tests never hit GitHub.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.utils import updater

# --------------------------------------------------------------------------- #
# Version comparison
# --------------------------------------------------------------------------- #


def test_is_newer_basic() -> None:
    assert updater.is_newer("1.1.0", "1.0.0") is True
    assert updater.is_newer("1.0.0", "1.0.0") is False
    assert updater.is_newer("2.0.0", "1.9.9") is True
    assert updater.is_newer("1.0.0", "1.1.0") is False


def test_is_newer_strips_v_prefix() -> None:
    assert updater.is_newer("v1.1.0", "1.0.0") is True
    assert updater.is_newer("1.1.0", "v1.0.0") is True
    assert updater.is_newer("v1.0.0", "v1.0.0") is False


def test_is_newer_falls_back_on_invalid_version() -> None:
    """Malformed tags fall back to lexicographic compare (never raise)."""
    assert isinstance(updater.is_newer("xyz", "abc"), bool)


# --------------------------------------------------------------------------- #
# Asset selection
# --------------------------------------------------------------------------- #


def test_select_windows_asset_prefers_x64_zip() -> None:
    assets = [
        {"name": "AgentTranslate-1.0.0-mac.zip"},
        {"name": "AgentTranslate-v1.1.0-windows-x64.zip"},
        {"name": "AgentTranslate-v1.1.0-linux.zip"},
        {"name": "checksums.txt"},
    ]
    picked = updater.select_windows_asset(assets)
    assert picked is not None
    assert picked["name"] == "AgentTranslate-v1.1.0-windows-x64.zip"


def test_select_windows_asset_without_x64_still_picks_windows() -> None:
    assets = [{"name": "AgentTranslate-v1.1.0-windows.zip"}]
    picked = updater.select_windows_asset(assets)
    assert picked is not None
    assert "windows" in picked["name"]


def test_select_windows_asset_none_when_absent() -> None:
    assert updater.select_windows_asset([{"name": "linux.zip"}, {"name": "mac.zip"}]) is None
    assert updater.select_windows_asset([]) is None


# --------------------------------------------------------------------------- #
# fetch_latest_release (mocked requests)
# --------------------------------------------------------------------------- #


def _fake_response(status=200, payload=None):
    class _R:
        def __init__(self):
            self.status_code = status
            self._payload = payload or {}

        def json(self):
            return self._payload

    return _R()


def test_fetch_latest_release_parses_tag_and_asset() -> None:
    payload = {
        "tag_name": "v1.2.0",
        "body": "Release notes here",
        "assets": [
            {"name": "AgentTranslate-v1.2.0-windows-x64.zip",
             "browser_download_url": "https://example.com/x.zip"},
        ],
    }
    with patch.object(updater.requests, "get", return_value=_fake_response(200, payload)):
        rel = updater.fetch_latest_release()
    assert rel.tag == "v1.2.0"
    assert rel.version == "1.2.0"
    assert rel.asset_url == "https://example.com/x.zip"
    assert rel.asset_name.endswith("windows-x64.zip")
    assert rel.notes == "Release notes here"


def test_fetch_latest_release_404_raises() -> None:
    with patch.object(updater.requests, "get", return_value=_fake_response(404)):
        with pytest.raises(updater.UpdateError, match="release"):
            updater.fetch_latest_release()


def test_fetch_latest_release_no_windows_asset_raises() -> None:
    payload = {"tag_name": "v1.2.0", "body": "", "assets": [{"name": "linux.zip"}]}
    with patch.object(updater.requests, "get", return_value=_fake_response(200, payload)):
        with pytest.raises(updater.UpdateError, match="Windows"):
            updater.fetch_latest_release()


def test_fetch_latest_release_network_error_raises() -> None:
    with patch.object(updater.requests, "get", side_effect=updater.requests.ConnectionError()):
        with pytest.raises(updater.UpdateError, match="Réseau"):
            updater.fetch_latest_release()


# --------------------------------------------------------------------------- #
# Dev mode / packaging detection
# --------------------------------------------------------------------------- #


def test_is_packaged_false_in_dev() -> None:
    """Under pytest/uv run the app is not frozen."""
    import sys
    assert not getattr(sys, "frozen", False)
    assert updater.is_packaged() is False


def test_get_current_version_is_string() -> None:
    v = updater.get_current_version()
    assert isinstance(v, str) and len(v) > 0

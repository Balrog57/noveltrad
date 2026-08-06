"""Tests for list_ollama_models (CDC Phase 1 — list models from local Ollama).

Network is mocked; tests never hit a real server.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core import llm


def _fake_resp(status=200, payload=None):
    class _R:
        def __init__(self):
            self.status_code = status
            self._payload = payload or {"models": []}

        def json(self):
            return self._payload

    return _R()


def test_list_ollama_models_parses_names() -> None:
    payload = {"models": [
        {"name": "qwen2.5:7b", "size": 100},
        {"name": "gemma2:9b", "size": 200},
    ]}
    with patch.object(llm.requests, "get", return_value=_fake_resp(200, payload)):
        models = llm.list_ollama_models()
    assert models == ["qwen2.5:7b", "gemma2:9b"]


def test_list_ollama_models_empty_when_no_models() -> None:
    with patch.object(llm.requests, "get", return_value=_fake_resp(200, {"models": []})):
        assert llm.list_ollama_models() == []


def test_list_ollama_models_filters_blank_names() -> None:
    payload = {"models": [{"name": "x:1"}, {"name": ""}, {"name": "y:2"}]}
    with patch.object(llm.requests, "get", return_value=_fake_resp(200, payload)):
        assert llm.list_ollama_models() == ["x:1", "y:2"]


def test_list_ollama_models_network_error_raises_connectionerror() -> None:
    with patch.object(llm.requests, "get", side_effect=llm.requests.ConnectionError()):
        with pytest.raises(ConnectionError):
            llm.list_ollama_models()


def test_list_ollama_models_http_error_raises_connectionerror() -> None:
    with patch.object(llm.requests, "get", return_value=_fake_resp(500)):
        with pytest.raises(ConnectionError):
            llm.list_ollama_models()


def test_list_ollama_models_uses_host_arg() -> None:
    """The host argument must drive the URL."""
    with patch.object(llm.requests, "get", return_value=_fake_resp(200)) as mock_get:
        llm.list_ollama_models("http://myhost:1234")
    called_url = mock_get.call_args.args[0]
    assert called_url == "http://myhost:1234/api/tags"

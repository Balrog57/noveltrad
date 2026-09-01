"""Regression tests for TTS route error responses (Sentinel).

TTS handlers previously echoed str(exception) in a ``details`` field, which can
leak filesystem paths or other internals to API clients.
"""
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from src.api.auth import API_TOKEN, register_auth
from src.api.blueprints.tts_routes import create_tts_blueprint


@pytest.fixture
def tts_client(tmp_path):
    app = Flask(__name__)
    register_auth(app)
    app.register_blueprint(create_tts_blueprint(str(tmp_path), MagicMock()))

    with app.test_client() as client:
        yield client


def test_voice_prompt_upload_hides_exception_details(tts_client):
    secret = "/secret/internal/path/leaked"

    with patch(
        "werkzeug.datastructures.FileStorage.save",
        side_effect=RuntimeError(secret),
    ):
        resp = tts_client.post(
            "/api/tts/voice-prompt/upload",
            headers={"X-API-Token": API_TOKEN},
            data={"file": (BytesIO(b"fake-audio"), "sample.wav")},
            content_type="multipart/form-data",
        )

    assert resp.status_code == 500
    body = resp.get_json()
    assert body == {"error": "Failed to save voice prompt"}
    assert secret not in resp.get_data(as_text=True)

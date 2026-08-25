"""Regression tests for /api/detect-language path containment."""
from unittest.mock import patch

import pytest
from flask import Flask

from src.api.blueprints.security_routes import create_security_blueprint


@pytest.fixture
def client(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "book.txt").write_text("hello", encoding="utf-8")

    evil = tmp_path / "uploads-evil"
    evil.mkdir()
    (evil / "secret.txt").write_text("secret", encoding="utf-8")

    app = Flask(__name__)
    app.register_blueprint(create_security_blueprint(str(tmp_path)))
    with app.test_client() as test_client:
        yield test_client, uploads, evil


class TestDetectLanguagePathContainment:
    def test_accepts_file_inside_uploads(self, client):
        test_client, uploads, _evil = client
        with patch(
            "src.api.blueprints.security_routes.LanguageDetector.detect_language_from_file",
            return_value=("en", 0.9),
        ):
            resp = test_client.post(
                "/api/detect-language",
                json={"file_path": str(uploads / "book.txt")},
            )
        assert resp.status_code == 200
        assert resp.get_json()["detected_language"] == "en"

    def test_rejects_sibling_prefix_directory(self, client):
        """'/uploads-evil' must not pass a startswith check against '/uploads'."""
        test_client, _uploads, evil = client
        resp = test_client.post(
            "/api/detect-language",
            json={"file_path": str(evil / "secret.txt")},
        )
        assert resp.status_code == 403
        assert "outside the uploads directory" in resp.get_json()["error"]

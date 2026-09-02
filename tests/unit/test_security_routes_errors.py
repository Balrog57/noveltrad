"""Regression tests for security route error responses (Sentinel follow-up).

Route handlers previously echoed str(exception) in a ``details`` field, which
can leak filesystem paths or other internals to API clients.
"""
from io import BytesIO
from unittest.mock import patch

import pytest
from flask import Flask

from src.api.auth import API_TOKEN, register_auth
from src.api.blueprints.security_routes import create_security_blueprint
from src.utils.security import SecurityError


@pytest.fixture
def security_client(tmp_path):
    app = Flask(__name__)
    register_auth(app)
    app.register_blueprint(create_security_blueprint(str(tmp_path)))

    with app.test_client() as client:
        yield client


def test_upload_security_error_hides_exception_details(security_client):
    secret = "/secret/internal/path/leaked"

    with patch(
        "src.api.blueprints.security_routes.SecureFileHandler.validate_and_save_file",
        side_effect=SecurityError(secret),
    ):
        resp = security_client.post(
            "/api/upload",
            data={"file": (BytesIO(b"hello"), "book.txt")},
            headers={"X-API-Token": API_TOKEN},
            content_type="multipart/form-data",
        )

    assert resp.status_code == 403
    body = resp.get_json()
    assert body == {"error": "Security validation failed"}
    assert secret not in resp.get_data(as_text=True)


def test_verify_upload_hides_exception_details(security_client, tmp_path):
    secret = "/secret/internal/path/leaked"
    uploads = tmp_path / "uploads"
    uploads.mkdir(exist_ok=True)
    inside = uploads / "book.txt"
    inside.write_text("ok", encoding="utf-8")

    with patch(
        "src.api.blueprints.security_routes.PathValidator.is_within_directory",
        side_effect=RuntimeError(secret),
    ):
        resp = security_client.post(
            "/api/uploads/verify",
            json={"file_paths": [str(inside)]},
            headers={"X-API-Token": API_TOKEN},
        )

    assert resp.status_code == 500
    body = resp.get_json()
    assert body == {"error": "Verification failed"}
    assert secret not in resp.get_data(as_text=True)

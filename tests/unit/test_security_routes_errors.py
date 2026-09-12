"""Regression tests for security route error responses (Sentinel follow-up to #35).

Route-level handlers previously echoed str(exception) in a ``details`` field,
which can leak filesystem paths or other internals to API clients.
"""
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

from src.api.auth import API_TOKEN, register_auth
from src.api.blueprints.security_routes import create_security_blueprint


@pytest.fixture
def security_client(tmp_path):
    app = Flask(__name__)
    register_auth(app)
    app.register_blueprint(create_security_blueprint(str(tmp_path)))

    with app.test_client() as client:
        yield client


def test_verify_uploaded_files_hides_exception_details(security_client, tmp_path):
    secret = "/secret/internal/path/leaked"
    uploads_dir = tmp_path / "uploads"
    safe_path = uploads_dir / "book.epub"
    safe_path.write_text("content")

    with patch.object(Path, "exists", side_effect=RuntimeError(secret)):
        resp = security_client.post(
            "/api/uploads/verify",
            json={"file_paths": [str(safe_path)]},
            headers={"X-API-Token": API_TOKEN},
        )

    assert resp.status_code == 500
    body = resp.get_json()
    assert body == {"error": "Verification failed"}
    assert secret not in resp.get_data(as_text=True)

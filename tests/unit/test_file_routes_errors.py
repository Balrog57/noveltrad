"""Regression tests for file route error responses (Sentinel follow-up to #32).

Route-level handlers previously echoed str(exception) in a ``details`` field,
which can leak filesystem paths or other internals to API clients.
"""
from unittest.mock import patch

import pytest
from flask import Flask

from src.api.auth import API_TOKEN, register_auth
from src.api.blueprints.file_routes import create_file_blueprint


@pytest.fixture
def file_client(tmp_path):
    app = Flask(__name__)
    register_auth(app)
    app.register_blueprint(create_file_blueprint(str(tmp_path)))

    with app.test_client() as client:
        yield client


def test_list_files_hides_exception_details(file_client):
    secret = "/secret/internal/path/leaked"

    with patch(
        "src.api.blueprints.file_routes.FileService.list_all_files",
        side_effect=RuntimeError(secret),
    ):
        resp = file_client.get("/api/files", headers={"X-API-Token": API_TOKEN})

    assert resp.status_code == 500
    body = resp.get_json()
    assert body == {"error": "Failed to list files"}
    assert secret not in resp.get_data(as_text=True)

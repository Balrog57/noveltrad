"""Regression tests for /api/uploads/verify path containment."""
import pytest
from flask import Flask

from src.api.auth import API_TOKEN, register_auth
from src.api.blueprints.security_routes import create_security_blueprint


@pytest.fixture
def client(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    uploads = output_dir / "uploads"
    uploads.mkdir()
    (uploads / "book.txt").write_text("content", encoding="utf-8")

    secret = tmp_path / "secret.env"
    secret.write_text("API_KEY=xxx", encoding="utf-8")

    app = Flask(__name__)
    register_auth(app)
    app.register_blueprint(create_security_blueprint(str(output_dir)))

    with app.test_client() as c:
        yield c, uploads, secret


def _auth_headers():
    return {"X-API-Token": API_TOKEN, "Content-Type": "application/json"}


def test_verify_accepts_existing_upload(client):
    test_client, uploads, _secret = client
    resp = test_client.post(
        "/api/uploads/verify",
        json={"file_paths": [str(uploads / "book.txt")]},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["existing"] == [str(uploads / "book.txt")]
    assert data["missing"] == []


def test_verify_rejects_paths_outside_uploads(client):
    test_client, uploads, secret = client
    resp = test_client.post(
        "/api/uploads/verify",
        json={
            "file_paths": [
                str(secret),
                str(uploads.parent / "uploads-evil" / "probe.txt"),
            ]
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["existing"] == []
    assert len(data["missing"]) == 2

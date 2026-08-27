"""Regression tests for path containment checks (issue #209 follow-up).

Several endpoints used str.startswith to decide whether a path lives inside the
uploads directory. That treats '/.../uploads-evil' as inside '/.../uploads'.
"""
from pathlib import Path

import pytest
from flask import Flask

from src.api import auth
from src.api.auth import register_auth, API_TOKEN
from src.api.blueprints.security_routes import create_security_blueprint
from src.api.services.file_service import FileService


@pytest.fixture
def sibling_dirs(tmp_path):
    """uploads/ and uploads-evil/ siblings with a file only in the latter."""
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    evil = tmp_path / "uploads-evil"
    evil.mkdir()
    victim = evil / "victim.txt"
    victim.write_text("do not delete", encoding="utf-8")
    return tmp_path, uploads, evil, victim


def test_delete_uploaded_file_rejects_sibling_prefix_directory(sibling_dirs):
    base, _uploads, _evil, victim = sibling_dirs
    svc = FileService(str(base))

    ok, error = svc.delete_uploaded_file(str(victim))

    assert ok is False
    assert "uploads directory" in error.lower()
    assert victim.exists()


@pytest.fixture
def security_client(sibling_dirs):
    base, uploads, _evil, victim = sibling_dirs
    app = Flask(__name__)
    register_auth(app)
    app.register_blueprint(create_security_blueprint(str(base)))

    with app.test_client() as client:
        yield client, uploads, victim


def test_verify_upload_rejects_path_outside_uploads(security_client):
    client, uploads, victim = security_client
    inside = uploads / "book.txt"
    inside.write_text("ok", encoding="utf-8")

    resp = client.post(
        "/api/uploads/verify",
        json={"file_paths": [str(inside), str(victim)]},
        headers={"X-API-Token": API_TOKEN},
    )

    assert resp.status_code == 403
    assert victim.exists()

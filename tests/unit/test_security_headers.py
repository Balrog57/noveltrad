"""Regression tests for baseline HTTP security headers."""
from flask import Flask

from src.api.security_headers import apply_security_headers


def test_apply_security_headers_sets_baseline_headers():
    app = Flask(__name__)

    @app.after_request
    def add_security_headers(response):
        return apply_security_headers(response)

    @app.route("/")
    def index():
        return "ok"

    with app.test_client() as client:
        resp = client.get("/")

    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in resp.headers.get("Permissions-Policy", "")


def test_apply_security_headers_does_not_overwrite_existing_values():
    app = Flask(__name__)

    @app.after_request
    def add_custom_frame_options(response):
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return apply_security_headers(response)

    @app.route("/")
    def index():
        return "ok"

    with app.test_client() as client:
        resp = client.get("/")

    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"

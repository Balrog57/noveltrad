"""Regression tests for global API error handlers."""
from flask import Flask

from src.api.routes import _register_error_handlers


def test_internal_server_error_hides_exception_details():
    app = Flask(__name__)
    _register_error_handlers(app)

    @app.route('/boom')
    def boom():
        raise RuntimeError("secret internal path /etc/shadow")

    with app.test_client() as client:
        resp = client.get('/boom')

    assert resp.status_code == 500
    body = resp.get_json()
    assert body == {"error": "Internal server error"}
    assert "shadow" not in resp.get_data(as_text=True)


def test_not_found_returns_generic_message():
    app = Flask(__name__)
    _register_error_handlers(app)

    with app.test_client() as client:
        resp = client.get('/missing-endpoint')

    assert resp.status_code == 404
    assert resp.get_json() == {"error": "API Endpoint not found"}

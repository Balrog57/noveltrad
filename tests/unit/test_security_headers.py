"""Regression tests for HTTP security response headers."""
import pytest
from flask import Flask

from translation_api import _SECURITY_HEADERS, _apply_response_headers


@pytest.fixture
def header_client():
    app = Flask(__name__)

    @app.route('/')
    def index():
        return 'ok'

    @app.after_request
    def _wrap(response):
        return _apply_response_headers(response)

    with app.test_client() as client:
        yield client


def test_security_headers_are_present(header_client):
    resp = header_client.get('/')
    assert resp.status_code == 200
    for header, value in _SECURITY_HEADERS.items():
        assert resp.headers.get(header) == value


def test_static_assets_still_no_store(header_client):
    resp = header_client.get('/static/js/index.js')
    assert resp.headers.get('Cache-Control') == 'no-store'
    assert resp.headers.get('X-Frame-Options') == 'DENY'

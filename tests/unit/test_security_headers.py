"""Regression tests for HTTP security headers on the web server."""
import pytest


@pytest.fixture
def client():
    from translation_api import app

    with app.test_client() as c:
        yield c


def test_security_headers_on_page_response(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert resp.headers.get('Permissions-Policy') == 'camera=(), microphone=(), geolocation=()'


def test_security_headers_on_api_response(client):
    from src.api.auth import API_TOKEN

    resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'

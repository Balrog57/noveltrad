"""Regression tests for baseline HTTP security headers."""
from translation_api import app


def test_responses_include_baseline_security_headers():
    with app.test_client() as client:
        resp = client.get('/api/health')

    assert resp.status_code == 200
    assert resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert 'camera=()' in resp.headers.get('Permissions-Policy', '')


def test_frontend_js_assets_are_not_cached():
    with app.test_client() as client:
        resp = client.get('/static/js/core/api-client.js')

    assert resp.status_code == 200
    assert resp.headers.get('Cache-Control') == 'no-store'
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'

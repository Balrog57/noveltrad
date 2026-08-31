"""Regression tests for baseline HTTP security headers on Flask responses."""
import pytest
from flask import Flask, jsonify

from src.api.auth import API_TOKEN, register_auth


@pytest.fixture
def client():
    app = Flask(__name__)
    register_auth(app)

    @app.after_request
    def _apply_response_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'no-referrer')
        response.headers.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=()',
        )
        return response

    def health_check():
        return jsonify({"status": "ok"})

    app.add_url_rule('/api/health', endpoint='config.health_check', view_func=health_check)

    with app.test_client() as test_client:
        yield test_client


def test_api_responses_include_security_headers(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'DENY'
    assert resp.headers.get('Referrer-Policy') == 'no-referrer'
    assert resp.headers.get('Permissions-Policy') == 'geolocation=(), microphone=(), camera=()'


def test_translation_api_app_applies_security_headers():
    import translation_api

    with translation_api.app.test_client() as client:
        resp = client.get('/api/health', headers={'X-API-Token': API_TOKEN})

    assert resp.status_code == 200
    assert resp.headers.get('X-Frame-Options') == 'DENY'
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'

"""Regression tests for baseline HTTP security response headers."""
from flask import Flask, make_response

from src.utils.security import apply_security_response_headers


def test_apply_security_response_headers_sets_baseline_headers():
    app = Flask(__name__)
    with app.app_context():
        response = make_response('ok')

        apply_security_response_headers(response)

        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert response.headers['X-Frame-Options'] == 'DENY'
        assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
        assert 'camera=()' in response.headers['Permissions-Policy']


def test_apply_security_response_headers_does_not_override_existing_values():
    app = Flask(__name__)
    with app.app_context():
        response = make_response('ok')
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        apply_security_response_headers(response)

        assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'

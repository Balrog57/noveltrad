"""Regression tests for upload rate-limit client IP resolution."""
from types import SimpleNamespace

from src.utils.security import get_client_ip


def _request(remote_addr, headers=None):
    return SimpleNamespace(remote_addr=remote_addr, headers=headers or {})


def test_get_client_ip_uses_remote_addr():
    assert get_client_ip(_request('203.0.113.10')) == '203.0.113.10'


def test_get_client_ip_ignores_spoofed_forwarded_for():
    """Clients must not be able to pick a fresh rate-limit bucket via headers."""
    req = _request('203.0.113.10', {'X-Forwarded-For': '198.51.100.1'})
    assert get_client_ip(req) == '203.0.113.10'


def test_get_client_ip_ignores_spoofed_real_ip():
    req = _request('203.0.113.10', {'X-Real-IP': '198.51.100.1'})
    assert get_client_ip(req) == '203.0.113.10'


def test_get_client_ip_defaults_when_remote_addr_missing():
    assert get_client_ip(_request(None)) == '127.0.0.1'

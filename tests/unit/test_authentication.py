"""Unit tests for AuthenticationService (SDD 7.6, 16.3)."""

from __future__ import annotations

import pytest

from noveltrad.core.exceptions import AuthenticationError
from noveltrad.core.security import PasswordVerifier
from noveltrad.modules.authentication.service import AuthenticationService


def test_not_configured():
    service = AuthenticationService(app_password=None)
    assert service.configured() is False
    with pytest.raises(AuthenticationError):
        service.authenticate("anything")


def test_correct_password():
    service = AuthenticationService(
        app_password="a-very-long-password", verifier=PasswordVerifier()
    )
    assert service.authenticate("a-very-long-password") is True


def test_wrong_password():
    service = AuthenticationService(
        app_password="a-very-long-password", verifier=PasswordVerifier()
    )
    assert service.authenticate("wrong-password") is False


def test_blocked_after_repeated_failures():
    verifier = PasswordVerifier(window_seconds=600, max_failures=3, block_seconds=60)
    service = AuthenticationService(app_password="a-very-long-password", verifier=verifier)
    for _ in range(2):
        service.authenticate("wrong")
    assert service.blocked() is False
    service.authenticate("wrong")  # third failure
    assert service.blocked() is True

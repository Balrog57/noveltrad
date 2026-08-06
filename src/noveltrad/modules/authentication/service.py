"""APP_PASSWORD authentication service (SDD 7.6, 16.3).

Reads and validates APP_PASSWORD without persisting or logging the secret.
Verification uses constant-time digest comparison; a global in-process
failure counter temporarily blocks attempts after repeated failures.
"""

from __future__ import annotations

from noveltrad.core.exceptions import AuthenticationError
from noveltrad.core.security import PasswordVerifier


class AuthenticationService:
    """Single-password authentication gate (no user accounts)."""

    def __init__(self, app_password: str | None, verifier: PasswordVerifier | None = None) -> None:
        self._app_password = app_password
        self._verifier = verifier or PasswordVerifier()

    def configured(self) -> bool:
        """True when APP_PASSWORD is defined in the environment (6.5)."""
        return self._app_password is not None

    def authenticate(self, password: str | None) -> bool:
        """Validate the supplied password; never logs the input."""
        if not self.configured():
            raise AuthenticationError("APP_PASSWORD is not configured")
        return self._verifier.verify(password, self._app_password)

    def blocked(self) -> bool:
        """True while the global failure lock is active."""
        blocked_until = self._verifier.blocked_until()
        if blocked_until is None:
            return False
        from time import monotonic

        return monotonic() < blocked_until

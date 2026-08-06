"""Closed exception taxonomy (SDD 7.18).

NovelTradError is the root; business errors are ValidationError,
NotFoundError, ConflictError, LockedError and AuthenticationError;
technical errors are StorageError, IntegrityError, ImportConversionError,
ContextWindowError, ProviderError and ResponseValidationError.
"""

from __future__ import annotations


class NovelTradError(Exception):
    """Root of the closed NovelTrad exception taxonomy."""


class BusinessError(NovelTradError):
    """Base class for business errors."""


class ValidationError(BusinessError):
    """Input or state validation failed."""


class NotFoundError(BusinessError):
    """A requested entity does not exist."""


class ConflictError(BusinessError):
    """An operation conflicts with the current state."""


class LockedError(BusinessError):
    """The resource is locked by an active translation."""


class AuthenticationError(BusinessError):
    """Authentication failed or is required."""


class StorageError(NovelTradError):
    """Filesystem or SQLite storage failure."""


class IntegrityError(StorageError):
    """A storage integrity constraint was violated."""


class ImportConversionError(StorageError):
    """Import conversion or validation failed.

    Carries a stable error_code and a safe_message without content.
    """

    def __init__(self, error_code: str, safe_message: str) -> None:
        self.error_code = error_code
        self.safe_message = safe_message
        super().__init__(f"{error_code}: {safe_message}")


class ContextWindowError(StorageError):
    """The model context window cannot hold the required content."""


class ProviderError(NovelTradError):
    """AI provider call failed.

    Carries a stable error_code, a recoverable flag and an optional
    retry_after_seconds. The safe representation never contains secrets
    or full content.
    """

    def __init__(
        self,
        error_code: str,
        recoverable: bool,
        retry_after_seconds: float | None = None,
        safe_message: str | None = None,
    ) -> None:
        self.error_code = error_code
        self.recoverable = recoverable
        self.retry_after_seconds = retry_after_seconds
        self.safe_message = safe_message or error_code
        super().__init__(self.safe_message)


class ResponseValidationError(ProviderError):
    """The provider returned an invalid response envelope."""

    def __init__(self, error_code: str, safe_message: str | None = None) -> None:
        super().__init__(error_code, recoverable=True, safe_message=safe_message)

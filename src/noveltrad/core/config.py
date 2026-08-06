"""Environment configuration (SDD 6.11) and APP_PASSWORD validation (6.5).

Closed set of operation options:
  - NOVELTRAD_BIND_ADDRESS: 127.0.0.1 or 0.0.0.0 (default 127.0.0.1)
  - NOVELTRAD_PORT: host port integer 1-65535 (default 8501)
  - NOVELTRAD_DATA_DIR: default /data
  - NOVELTRAD_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR or CRITICAL (default INFO)

APP_PASSWORD is read only from the environment and validated against the
bounds of SDD 6.5: at least 16 Unicode code points, at most 256 code points
and at most 1024 UTF-8 bytes, no NUL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from .exceptions import ValidationError

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@dataclass(frozen=True, slots=True)
class AppConfig:
    bind_address: Literal["127.0.0.1", "0.0.0.0"]
    port: int
    data_dir: str
    log_level: str
    app_password: str | None


def _validate_password(password: str | None) -> str | None:
    if password is None:
        return None
    if "\x00" in password:
        raise ValidationError("APP_PASSWORD contains a NUL character")
    code_points = len(password)
    if code_points < 16 or code_points > 256:
        raise ValidationError("APP_PASSWORD must contain between 16 and 256 Unicode code points")
    if len(password.encode("utf-8")) > 1024:
        raise ValidationError("APP_PASSWORD must not exceed 1024 UTF-8 bytes")
    return password


def _validate_bind(value: str) -> Literal["127.0.0.1", "0.0.0.0"]:
    if value not in ("127.0.0.1", "0.0.0.0"):
        raise ValidationError("NOVELTRAD_BIND_ADDRESS must be 127.0.0.1 or 0.0.0.0")
    return value  # type: ignore[return-value]


def _validate_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise ValidationError("NOVELTRAD_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValidationError("NOVELTRAD_PORT must be between 1 and 65535")
    return port


def _validate_log_level(value: str) -> str:
    if value not in _LOG_LEVELS:
        raise ValidationError(f"NOVELTRAD_LOG_LEVEL must be one of {', '.join(_LOG_LEVELS)}")
    return value


def load_config(env: dict[str, str] | None = None) -> AppConfig:
    """Load and validate the configuration from the environment.

    ``env`` defaults to os.environ; using an explicit mapping keeps the
    function deterministic for tests.
    """
    source = os.environ if env is None else env
    password = source.get("APP_PASSWORD")
    return AppConfig(
        bind_address=_validate_bind(source.get("NOVELTRAD_BIND_ADDRESS", "127.0.0.1")),
        port=_validate_port(source.get("NOVELTRAD_PORT", "8501")),
        data_dir=source.get("NOVELTRAD_DATA_DIR", "/data"),
        log_level=_validate_log_level(source.get("NOVELTRAD_LOG_LEVEL", "INFO")),
        app_password=_validate_password(password),
    )

"""Unit tests for core.config (SDD 6.11, 6.5)."""

from __future__ import annotations

import pytest

from noveltrad.core.config import load_config
from noveltrad.core.exceptions import ValidationError


def test_defaults():
    cfg = load_config({})
    assert cfg.bind_address == "127.0.0.1"
    assert cfg.port == 8501
    assert cfg.data_dir == "/data"
    assert cfg.log_level == "INFO"
    assert cfg.app_password is None


def test_full_override():
    cfg = load_config(
        {
            "APP_PASSWORD": "a" * 16,
            "NOVELTRAD_BIND_ADDRESS": "0.0.0.0",
            "NOVELTRAD_PORT": "9000",
            "NOVELTRAD_DATA_DIR": "/custom/data",
            "NOVELTRAD_LOG_LEVEL": "DEBUG",
        }
    )
    assert cfg.port == 9000
    assert cfg.bind_address == "0.0.0.0"
    assert cfg.data_dir == "/custom/data"
    assert cfg.log_level == "DEBUG"


def test_password_bounds():
    with pytest.raises(ValidationError):
        load_config({"APP_PASSWORD": "short"})
    with pytest.raises(ValidationError):
        load_config({"APP_PASSWORD": "a" * 257})
    with pytest.raises(ValidationError):
        load_config({"APP_PASSWORD": "a" * 16 + "\x00"})


def test_password_utf8_byte_limit():
    # 900 e-acute code points: 1800 UTF-8 bytes > 1024
    with pytest.raises(ValidationError):
        load_config({"APP_PASSWORD": "\u00e9" * 900})


def test_invalid_bind_and_port():
    with pytest.raises(ValidationError):
        load_config({"NOVELTRAD_BIND_ADDRESS": "1.2.3.4"})
    with pytest.raises(ValidationError):
        load_config({"NOVELTRAD_PORT": "0"})
    with pytest.raises(ValidationError):
        load_config({"NOVELTRAD_PORT": "70000"})
    with pytest.raises(ValidationError):
        load_config({"NOVELTRAD_PORT": "abc"})


def test_invalid_log_level():
    with pytest.raises(ValidationError):
        load_config({"NOVELTRAD_LOG_LEVEL": "VERBOSE"})

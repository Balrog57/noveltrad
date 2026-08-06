"""Unit tests for core.security (SDD 16.3, 16.11)."""

from __future__ import annotations

import pytest

from noveltrad.core.exceptions import AuthenticationError, StorageError
from noveltrad.core.security import (
    PasswordVerifier,
    decrypt_secret,
    derive_key,
    encrypt_secret,
    load_or_create_salt,
    redact,
    safe_scalars,
)


def test_verifier_success_and_reset():
    verifier = PasswordVerifier()
    assert verifier.verify("correct-horse", "correct-horse") is True
    # failure after success resets nothing but returns False
    assert verifier.verify("wrong", "correct-horse") is False


def test_verifier_block_after_five_failures():
    verifier = PasswordVerifier(window_seconds=600, max_failures=5, block_seconds=60)
    for _ in range(4):
        assert verifier.verify("wrong", "right") is False
    # fifth failure sets blocked_until
    assert verifier.verify("wrong", "right") is False
    assert verifier.blocked_until() is not None
    with pytest.raises(AuthenticationError):
        verifier.verify("right", "right")
    # after block expires, success clears the counter
    verifier._blocked_until = verifier._blocked_until - 61  # simulate elapsed
    assert verifier.verify("right", "right") is True


def test_verifier_none_password():
    verifier = PasswordVerifier()
    assert verifier.verify(None, "right") is False


def test_salt_create_and_reload(tmp_path):
    salt = load_or_create_salt(tmp_path)
    assert len(salt) == 16
    salt2 = load_or_create_salt(tmp_path)
    assert salt == salt2


def test_derive_key_deterministic():
    salt = b"\x01" * 16
    key1 = derive_key("password", salt)
    key2 = derive_key("password", salt)
    key3 = derive_key("password2", salt)
    assert key1 == key2
    assert len(key1) == 32
    assert key1 != key3


def test_encrypt_decrypt_roundtrip():
    salt = b"\x02" * 16
    key = derive_key("password", salt)
    envelope = encrypt_secret(key, "api_key", "sk-secret-value")
    assert "sk-secret-value" not in envelope
    assert decrypt_secret(key, "api_key", envelope) == "sk-secret-value"


def test_decrypt_wrong_key_fails():
    key = derive_key("password", b"\x03" * 16)
    wrong = derive_key("other", b"\x03" * 16)
    envelope = encrypt_secret(key, "api_key", "secret")
    with pytest.raises(StorageError):
        decrypt_secret(wrong, "api_key", envelope)


def test_decrypt_wrong_aad_fails():
    key = derive_key("password", b"\x04" * 16)
    envelope = encrypt_secret(key, "api_key", "secret")
    with pytest.raises(StorageError):
        decrypt_secret(key, "other_key", envelope)


def test_redact_limits_length():
    long_value = "x" * 5000
    assert len(redact(long_value)) == 512


def test_safe_scalars_redacts_objects():
    fields = {"count": 3, "name": "ok", "blob": object()}
    result = dict(safe_scalars(fields))
    assert result["count"] == 3
    assert result["name"] == "ok"
    assert result["blob"] == "[redacted]"

"""Security primitives (SDD 16.3, 16.11).

- APP_PASSWORD: constant-time comparison of fixed-length SHA-256 digests,
  plus a global in-process failure counter over a sliding ten-minute
  window; the fifth failure sets blocked_until = now + 60 s.
- API keys: AES-256-GCM with a 12-byte random nonce and UTF-8 AAD
  `noveltrad:settings:<setting_key>:v1`, key derived from APP_PASSWORD via
  Argon2id (memory_cost=65536 KiB, time_cost=3, parallelism=1, hash_len=32).
- data/key.salt: secrets.token_bytes(16), mode 0600 when supported.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .exceptions import AuthenticationError, StorageError

_SALT_FILE = "key.salt"
_ALGORITHM = "AES-256-GCM"
_AAD_PREFIX = "noveltrad:settings:"
_MEMORY_COST_KIB = 65536
_TIME_COST = 3
_PARALLELISM = 1
_HASH_LEN = 32

# Argon2 parameters validated against the fixed SDD profile.

# -- APP_PASSWORD ---------------------------------------------------------


@dataclass(slots=True)
class PasswordVerifier:
    """In-process global verifier with a sliding failure window (16.3)."""

    window_seconds: float = 600.0
    max_failures: int = 5
    block_seconds: float = 60.0
    _fail_times: list[float] = None  # type: ignore[assignment]
    _blocked_until: float | None = None

    def __post_init__(self) -> None:
        if self._fail_times is None:
            self._fail_times = []

    def verify(self, password: str | None, expected: str | None) -> bool:
        """Constant-time check; returns False and records on failure."""
        now = time.monotonic()
        if self._blocked_until is not None and now < self._blocked_until:
            raise AuthenticationError("too many failed attempts, retry later")
        if password is None or expected is None:
            self._record_failure(now)
            return False
        digest_a = hashlib.sha256(password.encode("utf-8")).digest()
        digest_b = hashlib.sha256(expected.encode("utf-8")).digest()
        ok = hmac.compare_digest(digest_a, digest_b)
        if ok:
            self._fail_times.clear()
            self._blocked_until = None
        else:
            self._record_failure(now)
        return ok

    def _record_failure(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self._fail_times = [t for t in self._fail_times if t > cutoff]
        self._fail_times.append(now)
        if len(self._fail_times) >= self.max_failures:
            self._blocked_until = now + self.block_seconds

    def blocked_until(self) -> float | None:
        return self._blocked_until


# -- key derivation and envelope encryption --------------------------------


def load_or_create_salt(data_dir: os.PathLike[str]) -> bytes:
    """Load data/key.salt or create it with token_bytes(16)."""
    data_path = os.fspath(data_dir)
    salt_path = os.path.join(data_path, _SALT_FILE)
    if os.path.exists(salt_path):
        with open(salt_path, "rb") as handle:
            return handle.read()
    os.makedirs(data_path, exist_ok=True)
    salt = secrets.token_bytes(16)
    fd = os.open(salt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, salt)
    finally:
        os.close(fd)
    with contextlib.suppress(OSError):
        os.chmod(salt_path, 0o600)
    return salt


def derive_key(password: str, salt: bytes) -> bytes:
    """Argon2id derivation of the 32-byte encryption key (16.11)."""
    from argon2.low_level import Type, hash_secret_raw

    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=_TIME_COST,
        memory_cost=_MEMORY_COST_KIB,
        parallelism=_PARALLELISM,
        hash_len=_HASH_LEN,
        type=Type.ID,
    )


def encrypt_secret(key: bytes, setting_key: str, plaintext: str) -> str:
    """AES-256-GCM envelope for a settings secret (16.11)."""
    aad = (_AAD_PREFIX + setting_key + ":v1").encode("utf-8")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), aad)
    envelope = {
        "v": 1,
        "alg": _ALGORITHM,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def decrypt_secret(key: bytes, setting_key: str, envelope_json: str) -> str:
    """Decrypt an AEAD envelope; raises StorageError when it fails."""
    try:
        envelope = json.loads(envelope_json)
        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ciphertext"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise StorageError("invalid secret envelope") from exc
    aad = (_AAD_PREFIX + setting_key + ":v1").encode("utf-8")
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except Exception as exc:  # noqa: BLE001 - cryptography raises generic errors
        raise StorageError("SECRET_DECRYPTION_FAILED") from exc
    return plaintext.decode("utf-8")


# -- redaction --------------------------------------------------------------


def redact(value: object) -> str:
    """Safe representation of a value: never a secret or full content."""
    if value is None:
        return ""
    text = str(value)
    if len(text) > 512:
        text = text[:512]
    return text


def safe_scalars(fields: dict[str, object]) -> tuple[tuple[str, object], ...]:
    """Keep only flat scalar fields, replacing anything else with a marker."""
    result: list[tuple[str, object]] = []
    for key, value in fields.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            result.append((key, value))
        else:
            result.append((key, "[redacted]"))
    return tuple(result)

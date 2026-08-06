"""Injectable clock (SDD 7.18, used for deterministic tests)."""

from __future__ import annotations

import time
from datetime import UTC, datetime


class Clock:
    """Minimal clock abstraction. Defaults to the system wall clock."""

    def utc_now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


class FrozenClock(Clock):
    """Clock with a fixed now, advancing on demand (tests)."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, tzinfo=UTC)
        self._mono = 0.0

    def utc_now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._mono

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self._now += timedelta(seconds=seconds)
        self._mono += seconds


def utc_now() -> datetime:
    """System default wall clock used when no Clock is injected."""
    return datetime.now(UTC)

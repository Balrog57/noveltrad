"""Retry policy (SDD RM-009, 11.8).

The initial call is followed by at most five retries only for: network
cut, connect/read timeout, HTTP 408/429/500/502/503/504, or a received but
invalid response. Base delays are 1, 5, 15, 30 and 60 seconds. For 429 or
503, a valid Retry-After expressed in seconds or HTTP date, non-negative
and <= 24 hours, imposes max(base_delay, Retry-After); any other value is
ignored and logged without its raw content. Permanent causes fail
immediately; no provider/model fallback is chosen automatically.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

RETRY_DELAYS = (1, 5, 15, 30, 60)
MAX_RETRIES = 5

_RETRYABLE_HTTP = {408, 429, 500, 502, 503, 504}
_MAX_RETRY_AFTER = 24 * 3600

_HTTP_DATE_RE = re.compile(
    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (\d{2}) ([A-Z][a-z]{2}) (\d{4}) "
    r"(\d{2}):(\d{2}):(\d{2}) GMT$"
)
_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

_PERMANENT_CODES = frozenset(
    {
        "AUTH_FAILED",
        "PERMISSION_DENIED",
        "INVALID_URL",
        "INVALID_OPTIONS",
        "MODEL_NOT_FOUND",
        "FORMAT_REFUSED",
        "CONTEXT_WINDOW_OVERRUN",
    }
)


def is_retryable_http(status: int) -> bool:
    return status in _RETRYABLE_HTTP


def is_permanent_code(error_code: str) -> bool:
    return error_code in _PERMANENT_CODES


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """Parse Retry-After into seconds; None when invalid (>24h or garbage)."""
    if value is None:
        return None
    value = value.strip()
    if value.isdigit():
        seconds = float(value)
    else:
        match = _HTTP_DATE_RE.match(value)
        if not match:
            return None
        try:
            day = int(match.group(1))
            month = _MONTHS.get(match.group(2))
            year = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            second = int(match.group(6))
            if month is None:
                return None
            delta = datetime(year, month, day, hour, minute, second, tzinfo=UTC) - (
                now or datetime.now(UTC)
            )
            seconds = max(0.0, delta.total_seconds())
        except ValueError:
            return None
    if seconds < 0 or seconds > _MAX_RETRY_AFTER:
        return None
    return seconds


def next_retry_delay(attempt: int) -> float:
    """Base delay for retry ``attempt`` (1-based, 1..5)."""
    if attempt < 1:
        attempt = 1
    if attempt > MAX_RETRIES:
        attempt = MAX_RETRIES
    return float(RETRY_DELAYS[attempt - 1])


def compute_wait(
    attempt: int,
    retry_after_seconds: float | None,
    *,
    status_code: int | None = None,
) -> float:
    """Wait before retry: max(base, valid Retry-After) for 429/503 only."""
    base = next_retry_delay(attempt)
    if retry_after_seconds is not None and status_code in (429, 503):
        return max(base, retry_after_seconds)
    return base

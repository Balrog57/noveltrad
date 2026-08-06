"""BEGIN IMMEDIATE transactions and units of work (SDD 8.3, 2.9).

Any business state modification runs inside an explicit SQLite transaction.
Concurrent writes and job takeover start with BEGIN IMMEDIATE. On failure a
full rollback is performed. Commit only after the documented phase of the
operation is satisfied.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Callable
from typing import TypeVar

from .exceptions import StorageError

T = TypeVar("T")


def in_transaction(
    conn: sqlite3.Connection, immediate: bool = True
) -> Callable[[Callable[..., T]], T]:
    """Decorator running the wrapped function inside one transaction.

    Example::

        @in_transaction(conn)
        def create_project(name: str) -> int:
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: object, **kwargs: object) -> T:
            try:
                conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
                result = func(*args, **kwargs)
                conn.commit()
                return result
            except sqlite3.Error as exc:
                with contextlib.suppress(sqlite3.Error):
                    conn.rollback()
                raise StorageError(f"transaction failed: {exc}") from exc
            except BaseException:
                with contextlib.suppress(sqlite3.Error):
                    conn.rollback()
                raise

        return wrapper

    return decorator


class UnitOfWork:
    """Context manager unit of work over the shared connection."""

    def __init__(self, conn: sqlite3.Connection, immediate: bool = True) -> None:
        self._conn = conn
        self._immediate = immediate
        self._active = False

    def __enter__(self) -> UnitOfWork:
        try:
            self._conn.execute("BEGIN IMMEDIATE" if self._immediate else "BEGIN")
        except sqlite3.Error as exc:
            raise StorageError(f"cannot begin transaction: {exc}") from exc
        self._active = True
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if not self._active:
            return
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        except sqlite3.Error as rollback_exc:
            raise StorageError(f"cannot finalize transaction: {rollback_exc}") from rollback_exc
        finally:
            self._active = False

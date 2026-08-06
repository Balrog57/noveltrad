"""SQLite connections, PRAGMA and versioned migrations (SDD 8.3, 8.11, 8.15).

Each process owns its own connection, never shared between threads. Every
connection executes PRAGMA foreign_keys=ON, busy_timeout=5000 and
synchronous=FULL at open; initialization sets journal_mode=WAL.

Migrations are applied at startup: read the highest schema_migrations.version,
apply each missing migration in order inside a transaction and record its
version only after success. A failed migration is fully rolled back and
blocks normal application startup. Before any migration that drops or
transforms a column/table, a logical SQLite backup is created under
data/backups/database-<UTC>-v<version>.sqlite, integrity-checked, keeping
the three most recent backups.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from .clock import utc_now
from .exceptions import IntegrityError, StorageError

_SCHEMA_MIGRATIONS = (
    "CREATE TABLE IF NOT EXISTS schema_migrations "
    "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
)

_BACKUPS_TO_KEEP = 3


def _split_statements(script: str) -> list[str]:
    """Split an SQL script into single statements, stripping comments.

    Executes inside an explicit transaction to keep migrations atomic;
    ``executescript`` is avoided because it commits implicitly.
    """
    statements: list[str] = []
    current: list[str] = []
    for raw_line in script.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        current.append(raw_line)
        if line.endswith(";"):
            statements.append("\n".join(current))
            current = []
    return statements


class Database:
    """Owned SQLite connection with migration support."""

    def __init__(self, path: Path, backups_dir: Path | None = None) -> None:
        self.path = Path(path)
        self.backups_dir = backups_dir or (self.path.parent / "backups")
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        try:
            conn = sqlite3.connect(self.path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA journal_mode=WAL")
            self._conn = conn
        except sqlite3.Error as exc:
            raise StorageError(f"cannot open SQLite database: {exc}") from exc

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise StorageError("database is not connected")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- migrations -------------------------------------------------------

    def _current_version(self) -> int:
        cur = self.conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations")
        return int(cur.fetchone()["v"])

    def migrate(self, migrations: Iterable[tuple[int, str]] | None = None) -> None:
        """Apply pending migrations in version order (SDD 8.15).

        ``migrations`` maps version -> SQL script. When None, the bundled
        migrations package under core/migrations/*.sql is used.
        """
        self.conn.execute(_SCHEMA_MIGRATIONS)
        self.conn.commit()
        if migrations is None:
            migrations = self._bundled_migrations()
        ordered = sorted(migrations, key=lambda item: item[0])
        current = self._current_version()
        for version, script in ordered:
            if version <= current:
                continue
            self._apply_one(version, script)

    def _bundled_migrations(self) -> list[tuple[int, str]]:
        import re

        directory = Path(__file__).resolve().parent / "migrations"
        result: list[tuple[int, str]] = []
        for file in sorted(directory.glob("*.sql")):
            match = re.match(r"(\d+)_", file.name)
            if not match:
                continue
            result.append((int(match.group(1)), file.read_text(encoding="utf-8")))
        return result

    def _apply_one(self, version: int, script: str) -> None:
        needs_backup = self._script_transforms(script)
        if needs_backup:
            self._backup(version)
        conn = self.conn
        try:
            conn.execute("BEGIN IMMEDIATE")
            for statement in _split_statements(script):
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, utc_now().isoformat()),
            )
            conn.commit()
        except sqlite3.Error as exc:
            with contextlib.suppress(sqlite3.Error):
                conn.rollback()
            raise StorageError(f"migration {version} failed: {exc}") from exc

    @staticmethod
    def _script_transforms(script: str) -> bool:
        lowered = script.lower()
        markers = ("drop table", "drop column", "alter table", "drop index")
        return any(marker in lowered for marker in markers)

    def _backup(self, version: int) -> None:
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        backup_path = (
            self.backups_dir / f"database-{utc_now().strftime('%Y%m%dT%H%M%S%z')}-v{version}.sqlite"
        )
        try:
            dest = sqlite3.connect(backup_path)
            self.conn.backup(dest)
            dest.close()
            self.conn.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.Error as exc:
            raise StorageError(f"migration backup failed: {exc}") from exc
        self._prune_backups()

    def _prune_backups(self) -> None:
        backups = sorted(self.backups_dir.glob("database-*-v*.sqlite"), reverse=True)
        for old in backups[_BACKUPS_TO_KEEP:]:
            with contextlib.suppress(OSError):
                old.unlink()

    def health(self) -> bool:
        """SELECT 1 in read-only mode (SDD 6.10)."""
        try:
            row = self.conn.execute("SELECT 1").fetchone()
            return row is not None and row[0] == 1
        except sqlite3.Error:
            return False


def initialize_schema(path: Path, backups_dir: Path | None = None) -> Database:
    """Open, initialize and migrate the database (idempotent)."""
    db = Database(path, backups_dir)
    db.connect()
    try:
        db.migrate()
    except sqlite3.Error as exc:
        raise IntegrityError(f"cannot initialize schema: {exc}") from exc
    return db

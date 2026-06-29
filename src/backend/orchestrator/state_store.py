"""State Store: single-writer SQLite + optional LanceDB vector layer.

Design (see .kilo/plans/multi-agent-pipeline-rewrite.md §3.1, §3.2):
- The orchestrator is the ONLY process that opens the SQLite connection.
- Agents never touch the store directly; they send {chunk_id, action}
  messages to the orchestrator, which performs reads/writes on their behalf.
- This avoids SQLite writer contention and keeps the message queues light
  (UUIDs only, never full chunk text).
- LanceDB is optional; the store degrades gracefully if it is missing
  (ConsistencyChecker falls back to TF-IDF cosine similarity, see §9).

Public surface used by the orchestrator (unchanged by the v4 split):
    store = StateStore(db_path, vector_dir=...)
    store.add_chunk(chunk_dict)
    store.get_chunk(chunk_id) -> dict | None
    store.update_chunk_field(chunk_id, field, value)
    store.list_chunks(status=None) -> list[dict]
    store.add_lexicon_term(term_dict)
    store.list_lexicon() -> list[dict]
    store.add_qa_issue(issue_dict)
    store.add_grammar_issue(issue_dict)
    store.add_consistency_flag(flag_dict)
    store.set_state(key, value)
    store.get_state(key) -> str | None
    store.close()

The store is NOT thread-safe across processes. It must be created
fresh in the orchestrator process; child agents must not import it.

Implementation note
-------------------
This module used to be a 972-line monolith with 44 methods on one class.
It is now a thin facade (~300 lines) that wires per-table repositories
defined in :mod:`.repositories`. The repositories share the store's
single ``sqlite3.Connection`` and ``threading.RLock``; they never open
their own connection. Splitting this up gives us:

  * One file per logical area (chunks / lexicon / issues / hltl / kv /
    projects / snapshot) -- each ~50-150 lines, easy to navigate.
  * StateStore becomes a focused facade: it owns the connection
    lifetime, the migrations, the optional vector store, the
    ``transaction()`` context manager, and the ``clear_project_data``
    cross-table reset. Everything else is a one-line delegate.
  * Tests and future contributors can target one repository at a time
    without paging through unrelated SQL.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from .repositories import (
    ChunkRepo,
    HltlRepo,
    IssueRepo,
    LexiconRepo,
    ProjectRepo,
    SnapshotReader,
    StateKV,
)

logger = logging.getLogger(__name__)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    chapter_id TEXT NOT NULL,
    chapter_title TEXT,
    chunk_index INTEGER NOT NULL,
    source_text TEXT NOT NULL,
    source_hash TEXT,
    glossary_version TEXT,
    output_hash TEXT,
    raw_translation TEXT,
    glossary_applied TEXT,
    llm_refined TEXT,
    qa_checked TEXT,
    grammar_checked TEXT,
    polished_translation TEXT,
    status TEXT DEFAULT 'parsed',
    error_message TEXT,
    review_score REAL DEFAULT NULL,
    review_annotations TEXT DEFAULT NULL,
    metadata_json TEXT,
    source_file TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_chunks_status ON chunks(status);
CREATE INDEX IF NOT EXISTS idx_chunks_chapter ON chunks(chapter_id);

CREATE TABLE IF NOT EXISTS lexicon_terms (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    aliases_json TEXT,
    category TEXT,
    gender TEXT DEFAULT 'unknown',
    confidence REAL DEFAULT 0.0,
    evidence_refs_json TEXT,
    notes TEXT,
    validated_by_user INTEGER DEFAULT 0,
    chapter_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_lexicon_source ON lexicon_terms(source);

CREATE TABLE IF NOT EXISTS qa_issues (
    id TEXT PRIMARY KEY,
    chunk_id TEXT REFERENCES chunks(id),
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    auto_fixed INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_qa_chunk ON qa_issues(chunk_id);

CREATE TABLE IF NOT EXISTS grammar_issues (
    id TEXT PRIMARY KEY,
    chunk_id TEXT REFERENCES chunks(id),
    start_pos INTEGER,
    end_pos INTEGER,
    message TEXT NOT NULL,
    suggestion TEXT,
    applied INTEGER DEFAULT 0,
    rule_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_grammar_chunk ON grammar_issues(chunk_id);

CREATE TABLE IF NOT EXISTS consistency_flags (
    id TEXT PRIMARY KEY,
    chunk_id TEXT REFERENCES chunks(id),
    source_term TEXT,
    expected_translation TEXT,
    found_translation TEXT,
    confidence REAL,
    resolved INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_consistency_chunk ON consistency_flags(chunk_id);

CREATE TABLE IF NOT EXISTS pipeline_state (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS pending_hltl (
    request_id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    issue_json TEXT NOT NULL,
    received_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_hltl_chunk ON pending_hltl(chunk_id);
CREATE INDEX IF NOT EXISTS idx_hltl_unresolved
    ON pending_hltl(resolved_at) WHERE resolved_at IS NULL;
"""


class StateStore:
    """Single-writer SQLite wrapper for the orchestrator.

    Owns the SQLite connection lifetime, the migration runner, the
    optional LanceDB vector layer, and the ``transaction()`` context
    manager. Per-table CRUD lives in :mod:`.repositories`; the public
    methods here are one-line delegates to the matching repository.

    The orchestrator process is expected to instantiate one StateStore
    and never share it across process boundaries. For thread-safety
    within the orchestrator (FastAPI handlers + background loop), a
    re-entrant lock guards all writes; reads use the same connection
    with WAL mode for safe concurrent readers in the same process.
    """

    def __init__(self, db_path: str | Path, vector_dir: str | Path | None = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector_dir = Path(vector_dir) if vector_dir else None
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # autocommit; we manage transactions explicitly
        )
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.DatabaseError as exc:
            logger.warning("PRAGMA setup failed (non-fatal): %s", exc)
        # Idempotent in-place migrations for DBs created by older
        # versions of NovelTrad (4.0.0 and earlier don't have the
        # `source_file` column on `chunks`).
        self._apply_migrations()
        self._conn.executescript(SCHEMA_SQL)
        # Defensive index creation: this index lives on a column that
        # didn't exist before 4.0.1, so it can't be in SCHEMA_SQL
        # (which is run on every open).
        self._safe_create_index(
            "idx_chunks_source_file", "chunks", "source_file"
        )

        self._vector = None
        self._vector_import_error: str | None = None
        if self.vector_dir is not None:
            self._init_vector_store()

        # Wire the repositories. They share this store's connection and
        # lock; they never open their own. Adding a new repo? Build it
        # in repositories.py and instantiate it here.
        self.chunks = ChunkRepo(self._conn, self._lock)
        self.lexicon = LexiconRepo(self._conn, self._lock)
        self.issues = IssueRepo(self._conn, self._lock)
        self.hltl = HltlRepo(self._conn, self._lock)
        self.kv = StateKV(self._conn, self._lock)
        self.projects = ProjectRepo(self._conn, self._lock, self.kv)
        # ``vector_status`` is a property on this class, so passing it
        # as ``vector_status=self.vector_status`` would evaluate the
        # property once at construction and freeze the result. Wrap it
        # in a lambda so SnapshotReader reads the live status on every
        # build.
        self._snapshot = SnapshotReader(
            self._conn, self._lock, vector_status=lambda: self.vector_status
        )

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _apply_migrations(self) -> None:
        """Idempotent column-level migrations for pre-4.0.1 DBs."""
        with self._lock:
            self._safe_add_column("chunks", "source_file", "TEXT DEFAULT ''")
            self._safe_add_column("chunks", "review_score", "REAL DEFAULT NULL")
            self._safe_add_column("chunks", "review_annotations", "TEXT DEFAULT NULL")
            self._safe_add_column("chunks", "llm_refined", "TEXT DEFAULT NULL")

    def _safe_add_column(
        self, table: str, column: str, definition: str
    ) -> None:
        try:
            self._conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )
            logger.info("Migration: added %s.%s", table, column)
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            # "duplicate column name" -> already migrated (idempotent OK).
            # "no such table" -> fresh DB, SCHEMA_SQL will create the
            # column from the CREATE TABLE statement; no migration needed.
            if "duplicate column" in msg or "no such table" in msg:
                return
            logger.warning(
                "Migration: failed to add %s.%s: %s", table, column, exc
            )

    def _safe_create_index(
        self, name: str, table: str, column: str
    ) -> None:
        try:
            self._conn.execute(
                f"CREATE INDEX IF NOT EXISTS {name} ON {table}({column})"
            )
        except sqlite3.OperationalError as exc:
            logger.debug("Index %s skipped: %s", name, exc)

    def _init_vector_store(self) -> None:
        """Try to attach LanceDB. Soft-fail: store still works without it."""
        try:
            import lancedb  # type: ignore

            self.vector_dir.mkdir(parents=True, exist_ok=True)
            self._vector = lancedb.connect(str(self.vector_dir))
            logger.info("LanceDB vector store attached at %s", self.vector_dir)
        except Exception as exc:  # ImportError or runtime error
            self._vector = None
            self._vector_import_error = repr(exc)
            logger.warning(
                "LanceDB unavailable (%s); consistency RAG will fall back "
                "to TF-IDF. Install lancedb to enable full RAG mode.",
                exc,
            )

    @property
    def vector_available(self) -> bool:
        return self._vector is not None

    @property
    def vector_status(self) -> str:
        if self._vector is not None:
            return f"lancedb @ {self.vector_dir}"
        if self._vector_import_error:
            return f"disabled: {self._vector_import_error}"
        return "disabled (no vector_dir configured)"

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Explicit SQLite transaction context manager.

        All writes inside the ``with`` block are committed atomically.
        If an exception is raised, the transaction is rolled back.

        Requires ``isolation_level=None`` on the connection (already set
        in the constructor), which puts us in manual-commit mode so
        ``BEGIN`` / ``COMMIT`` statements are respected.

        Usage::

            with store.transaction():
                store.update_chunk_field(chunk_id, "status", "parsed")
                store.add_grammar_issue({...})
        """
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            with self._lock:
                self._conn.execute("ROLLBACK")
            raise
        with self._lock:
            self._conn.execute("COMMIT")

    def clear_project_data(self) -> None:
        """Clear per-project pipeline rows from the active SQLite store.

        The MVP backend currently runs one active project per backend
        process. Until the schema carries project_id on every table,
        starting a new project must clear old chunks/issues so the
        assembler cannot mix content from previous runs.

        This is a cross-table reset, so it intentionally lives on the
        facade rather than in any one repository.
        """
        with self._lock:
            self._conn.execute("DELETE FROM consistency_flags")
            self._conn.execute("DELETE FROM grammar_issues")
            self._conn.execute("DELETE FROM qa_issues")
            self._conn.execute("DELETE FROM lexicon_terms")
            self._conn.execute("DELETE FROM pending_hltl")
            self._conn.execute("DELETE FROM chunks")
            self._conn.execute(
                """
                DELETE FROM pipeline_state
                WHERE key IN (
                    'current_project',
                    'output_artifact',
                    'project_manifest_path',
                    'target_path'
                )
                OR key LIKE 'hltl_response:%'
                """
            )

    # ------------------------------------------------------------------
    # chunks (delegate to ChunkRepo)
    # ------------------------------------------------------------------

    def add_chunk(self, chunk: dict[str, Any]) -> None:
        self.chunks.add(chunk)

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        return self.chunks.get(chunk_id)

    def update_chunk_field(self, chunk_id: str, field: str, value: Any) -> None:
        self.chunks.update_field(chunk_id, field, value)

    def list_chunks(
        self,
        status: str | None = None,
        chapter_id: str | None = None,
        source_file: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        return self.chunks.list(
            status=status,
            chapter_id=chapter_id,
            source_file=source_file,
            limit=limit,
            offset=offset,
        )

    def count_chunks(self, status: str | None = None) -> int:
        return self.chunks.count(status=status)

    # ------------------------------------------------------------------
    # lexicon (delegate to LexiconRepo)
    # ------------------------------------------------------------------

    def add_lexicon_term(self, term: dict[str, Any]) -> None:
        self.lexicon.add(term)

    def list_lexicon(self) -> list[dict[str, Any]]:
        return self.lexicon.list()

    def find_lexicon_by_source(self, source: str) -> dict[str, Any] | None:
        return self.lexicon.find_by_source(source)

    def upsert_lexicon_term(self, term: dict[str, Any]) -> None:
        self.lexicon.upsert(term)

    def update_lexicon_term(self, term_id: str, updates: dict[str, Any]) -> None:
        self.lexicon.update(term_id, updates)

    def delete_lexicon_term(self, term_id: str) -> bool:
        return self.lexicon.delete(term_id)

    # ------------------------------------------------------------------
    # qa / grammar / consistency issues (delegate to IssueRepo)
    # ------------------------------------------------------------------

    def add_qa_issue(self, issue: dict[str, Any]) -> None:
        self.issues.add_qa(issue)

    def add_grammar_issue(self, issue: dict[str, Any]) -> None:
        self.issues.add_grammar(issue)

    def add_consistency_flag(self, flag: dict[str, Any]) -> None:
        self.issues.add_consistency(flag)

    def list_qa_issues(self, chunk_id: str) -> list[dict[str, Any]]:
        return self.issues.list_qa(chunk_id)

    def list_grammar_issues(self, chunk_id: str) -> list[dict[str, Any]]:
        return self.issues.list_grammar(chunk_id)

    def list_consistency_flags(self, chunk_id: str) -> list[dict[str, Any]]:
        return self.issues.list_consistency(chunk_id)

    # ------------------------------------------------------------------
    # pipeline_state key/value (delegate to StateKV)
    # ------------------------------------------------------------------

    def set_state(self, key: str, value: Any) -> None:
        self.kv.set(key, value)

    def get_state(self, key: str) -> str | None:
        return self.kv.get(key)

    def get_state_json(self, key: str, default: Any = None) -> Any:
        return self.kv.get_json(key, default)

    # ------------------------------------------------------------------
    # pending_hltl (delegate to HltlRepo)
    # ------------------------------------------------------------------

    def register_hltl_record(
        self,
        request_id: str,
        chunk_id: str,
        stage: str,
        issue: dict[str, Any],
        received_at: str,
    ) -> None:
        self.hltl.register(request_id, chunk_id, stage, issue, received_at)

    def resolve_hltl_record(self, request_id: str, resolved_at: str) -> None:
        self.hltl.resolve(request_id, resolved_at)

    def list_unresolved_hltl(self) -> list[dict[str, Any]]:
        return self.hltl.list_unresolved()

    def clear_hltl_records(self) -> None:
        self.hltl.clear()

    # ------------------------------------------------------------------
    # projects (delegate to ProjectRepo)
    # ------------------------------------------------------------------

    def list_projects(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        return self.projects.list(limit=limit, offset=offset)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self.projects.get(project_id)

    def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
        return self.projects.update(project_id, updates)

    def delete_project(self, project_id: str) -> bool:
        return self.projects.delete(project_id)

    def set_active_project(self, project_id: str) -> None:
        self.projects.set_active(project_id)

    def get_active_project(self) -> str | None:
        return self.projects.get_active()

    def clear_active_project(self) -> None:
        self.projects.clear_active()

    def forget_project(self, project_id: str) -> None:
        self.projects.forget(project_id)

    # ------------------------------------------------------------------
    # diagnostics
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        return self._snapshot.build()


__all__ = ["StateStore", "SCHEMA_SQL"]

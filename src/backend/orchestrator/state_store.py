"""State Store: single-writer SQLite + optional LanceDB vector layer.

Design (see .kilo/plans/multi-agent-pipeline-rewrite.md §3.1, §3.2):
- The orchestrator is the ONLY process that opens the SQLite connection.
- Agents never touch the store directly; they send {chunk_id, action}
  messages to the orchestrator, which performs reads/writes on their behalf.
- This avoids SQLite writer contention and keeps the message queues light
  (UUIDs only, never full chunk text).
- LanceDB is optional; the store degrades gracefully if it is missing
  (ConsistencyChecker falls back to TF-IDF cosine similarity, see §9).

Public surface used by the orchestrator:
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
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

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
    qa_checked TEXT,
    grammar_checked TEXT,
    polished_translation TEXT,
    status TEXT DEFAULT 'parsed',
    error_message TEXT,
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

    def _apply_migrations(self) -> None:
        """Idempotent column-level migrations for pre-4.0.1 DBs."""
        with self._lock:
            self._safe_add_column("chunks", "source_file", "TEXT DEFAULT ''")

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
            # "duplicate column name" → already migrated (idempotent OK).
            # "no such table" → fresh DB, SCHEMA_SQL will create the
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

    def clear_project_data(self) -> None:
        """Clear per-project pipeline rows from the active SQLite store.

        The MVP backend currently runs one active project per backend
        process. Until the schema carries project_id on every table,
        starting a new project must clear old chunks/issues so the
        assembler cannot mix content from previous runs.
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
                OR key LIKE 'project:%'
                OR key LIKE 'hltl_response:%'
                """
            )

    # ---------- chunks ----------

    def add_chunk(self, chunk: dict[str, Any]) -> None:
        meta = chunk.get("metadata") or {}
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO chunks (
                    id, chapter_id, chapter_title, chunk_index, source_text,
                    source_hash, glossary_version, output_hash,
                    raw_translation, glossary_applied, qa_checked,
                    grammar_checked, polished_translation,
                    status, error_message, metadata_json, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk["id"],
                    chunk["chapter_id"],
                    chunk.get("chapter_title"),
                    chunk["chunk_index"],
                    chunk["source_text"],
                    chunk.get("source_hash"),
                    chunk.get("glossary_version"),
                    chunk.get("output_hash"),
                    chunk.get("raw_translation"),
                    chunk.get("glossary_applied"),
                    chunk.get("qa_checked"),
                    chunk.get("grammar_checked"),
                    chunk.get("polished_translation"),
                    chunk.get("status", "parsed"),
                    chunk.get("error_message"),
                    json.dumps(meta, ensure_ascii=False) if meta else None,
                    chunk.get("source_file", ""),
                ),
            )

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM chunks WHERE id = ?", (chunk_id,)
            ).fetchone()
        return _row_to_chunk(row) if row else None

    def update_chunk_field(self, chunk_id: str, field: str, value: Any) -> None:
        allowed = {
            "raw_translation",
            "glossary_applied",
            "qa_checked",
            "grammar_checked",
            "polished_translation",
            "status",
            "error_message",
            "source_hash",
            "glossary_version",
            "output_hash",
        }
        if field not in allowed:
            raise ValueError(f"Refusing to update non-allowlisted field: {field}")
        with self._lock:
            self._conn.execute(
                f"UPDATE chunks SET {field} = ? WHERE id = ?", (value, chunk_id)
            )

    def list_chunks(
        self,
        status: str | None = None,
        chapter_id: str | None = None,
        source_file: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM chunks"
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if chapter_id is not None:
            clauses.append("chapter_id = ?")
            params.append(chapter_id)
        if source_file is not None:
            clauses.append("source_file = ?")
            params.append(source_file)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY source_file, chapter_id, chunk_index"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        if offset is not None and offset > 0:
            query += f" OFFSET {int(offset)}"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [_row_to_chunk(r) for r in rows]

    def count_chunks(self, status: str | None = None) -> int:
        with self._lock:
            if status is None:
                row = self._conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
            else:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS n FROM chunks WHERE status = ?", (status,)
                ).fetchone()
        return int(row["n"]) if row else 0

    # ---------- lexicon ----------

    def add_lexicon_term(self, term: dict[str, Any]) -> None:
        aliases = term.get("aliases") or []
        evidence = term.get("evidence_refs") or []
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO lexicon_terms (
                    id, source, target, aliases_json, category, gender,
                    confidence, evidence_refs_json, notes,
                    validated_by_user, chapter_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    term["id"],
                    term["source"],
                    term["target"],
                    json.dumps(aliases, ensure_ascii=False) if aliases else None,
                    term.get("category"),
                    term.get("gender", "unknown"),
                    float(term.get("confidence", 0.0)),
                    (
                        json.dumps(evidence, ensure_ascii=False)
                        if evidence
                        else None
                    ),
                    term.get("notes"),
                    1 if term.get("validated_by_user") else 0,
                    term.get("chapter_id"),
                ),
            )

    def list_lexicon(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM lexicon_terms ORDER BY source"
            ).fetchall()
        return [_row_to_lexicon(r) for r in rows]

    def update_lexicon_term(self, term_id: str, updates: dict[str, Any]) -> None:
        if not updates:
            return
        allowed = {
            "source",
            "target",
            "category",
            "gender",
            "confidence",
            "notes",
            "validated_by_user",
        }
        cols = []
        params: list[Any] = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "validated_by_user":
                value = 1 if value else 0
            cols.append(f"{key} = ?")
            params.append(value)
        if not cols:
            return
        params.append(term_id)
        with self._lock:
            self._conn.execute(
                f"UPDATE lexicon_terms SET {', '.join(cols)} WHERE id = ?", params
            )

    def delete_lexicon_term(self, term_id: str) -> bool:
        """Hard-delete a lexicon term. Returns True if a row was removed."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM lexicon_terms WHERE id = ?", (term_id,)
            )
            self._conn.commit()
            return cur.rowcount > 0

    # ---------- QA / grammar / consistency ----------

    def add_qa_issue(self, issue: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO qa_issues (
                    id, chunk_id, issue_type, severity, message, auto_fixed
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    issue["id"],
                    issue["chunk_id"],
                    issue["issue_type"],
                    issue["severity"],
                    issue["message"],
                    1 if issue.get("auto_fixed") else 0,
                ),
            )

    def add_grammar_issue(self, issue: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO grammar_issues (
                    id, chunk_id, start_pos, end_pos, message,
                    suggestion, applied, rule_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    issue["id"],
                    issue["chunk_id"],
                    issue.get("start_pos"),
                    issue.get("end_pos"),
                    issue["message"],
                    issue.get("suggestion"),
                    1 if issue.get("applied") else 0,
                    issue.get("rule_id"),
                ),
            )

    def add_consistency_flag(self, flag: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO consistency_flags (
                    id, chunk_id, source_term, expected_translation,
                    found_translation, confidence, resolved
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    flag["id"],
                    flag["chunk_id"],
                    flag.get("source_term"),
                    flag.get("expected_translation"),
                    flag.get("found_translation"),
                    float(flag.get("confidence", 0.0)),
                    1 if flag.get("resolved") else 0,
                ),
            )

    def list_qa_issues(self, chunk_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM qa_issues WHERE chunk_id = ? ORDER BY id",
                (chunk_id,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "chunk_id": r["chunk_id"],
                "issue_type": r["issue_type"],
                "severity": r["severity"],
                "message": r["message"],
                "auto_fixed": bool(r["auto_fixed"]),
            }
            for r in rows
        ]

    def list_grammar_issues(self, chunk_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM grammar_issues WHERE chunk_id = ? ORDER BY id",
                (chunk_id,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "chunk_id": r["chunk_id"],
                "start_pos": r["start_pos"],
                "end_pos": r["end_pos"],
                "message": r["message"],
                "suggestion": r["suggestion"],
                "applied": bool(r["applied"]),
                "rule_id": r["rule_id"],
            }
            for r in rows
        ]

    def list_consistency_flags(self, chunk_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM consistency_flags WHERE chunk_id = ? ORDER BY id",
                (chunk_id,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "chunk_id": r["chunk_id"],
                "source_term": r["source_term"],
                "expected_translation": r["expected_translation"],
                "found_translation": r["found_translation"],
                "confidence": r["confidence"],
                "resolved": bool(r["resolved"]),
            }
            for r in rows
        ]

    # ---------- pipeline state key/value ----------

    def set_state(self, key: str, value: Any) -> None:
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO pipeline_state (key, value) VALUES (?, ?)",
                (key, value),
            )

    def get_state(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM pipeline_state WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def get_state_json(self, key: str, default: Any = None) -> Any:
        raw = self.get_state(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    # ---------- pending_hltl (persistent HITL queue) ----------

    def register_hltl_record(
        self,
        request_id: str,
        chunk_id: str,
        stage: str,
        issue: dict[str, Any],
        received_at: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO pending_hltl (
                    request_id, chunk_id, stage, issue_json, received_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (
                    request_id,
                    chunk_id,
                    stage,
                    json.dumps(issue, ensure_ascii=False),
                    received_at,
                ),
            )

    def resolve_hltl_record(self, request_id: str, resolved_at: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE pending_hltl SET resolved_at = ? WHERE request_id = ?",
                (resolved_at, request_id),
            )

    def list_unresolved_hltl(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT request_id, chunk_id, stage, issue_json, received_at
                FROM pending_hltl
                WHERE resolved_at IS NULL
                ORDER BY received_at
                """
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            try:
                issue = json.loads(r["issue_json"])
            except json.JSONDecodeError:
                issue = {}
            out.append(
                {
                    "request_id": r["request_id"],
                    "chunk_id": r["chunk_id"],
                    "stage": r["stage"],
                    "issue": issue,
                    "received_at": r["received_at"],
                }
            )
        return out

    def clear_hltl_records(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM pending_hltl")

    # ---------- diagnostics ----------

    def snapshot(self) -> dict[str, Any]:
        """Cheap summary used by GET /pipeline/state."""

        # ⚡ Bolt optimization: Batch chunk counting into a single query
        # instead of N+1 separate queries per status.
        expected_statuses = (
            "parsed",
            "fast_translated",
            "lexicon_ready",
            "lexicon_skipped",
            "glossary_applied",
            "consistency_checked",
            "qa_checked",
            "grammar_checked",
            "polished",
            "assembled",
            "waiting_for_human",
            "error",
        )
        chunks_by_status = {s: 0 for s in expected_statuses}
        chunks_total = 0

        with self._lock:
            rows = self._conn.execute("SELECT status, COUNT(*) as n FROM chunks GROUP BY status").fetchall()
            for r in rows:
                status = r["status"]
                count = int(r["n"])
                if status in chunks_by_status:
                    chunks_by_status[status] = count
                chunks_total += count

        return {
            "chunks_total": chunks_total,
            "chunks_by_status": chunks_by_status,
            "lexicon_terms": self._scalar("SELECT COUNT(*) FROM lexicon_terms"),
            "qa_issues": self._scalar("SELECT COUNT(*) FROM qa_issues"),
            "grammar_issues": self._scalar("SELECT COUNT(*) FROM grammar_issues"),
            "consistency_flags": self._scalar(
                "SELECT COUNT(*) FROM consistency_flags"
            ),
            "pending_hltl": self._scalar(
                "SELECT COUNT(*) FROM pending_hltl WHERE resolved_at IS NULL"
            ),
            "vector_store": self.vector_status,
        }

    def _scalar(self, sql: str) -> int:
        with self._lock:
            row = self._conn.execute(sql).fetchone()
        return int(row[0]) if row else 0


# ---------- helpers ----------


def _row_to_chunk(row: sqlite3.Row) -> dict[str, Any]:
    meta_raw = row["metadata_json"]
    metadata = json.loads(meta_raw) if meta_raw else {}
    return {
        "id": row["id"],
        "chapter_id": row["chapter_id"],
        "chapter_title": row["chapter_title"],
        "chunk_index": row["chunk_index"],
        "source_text": row["source_text"],
        "source_hash": row["source_hash"],
        "glossary_version": row["glossary_version"],
        "output_hash": row["output_hash"],
        "raw_translation": row["raw_translation"],
        "glossary_applied": row["glossary_applied"],
        "qa_checked": row["qa_checked"],
        "grammar_checked": row["grammar_checked"],
        "polished_translation": row["polished_translation"],
        "status": row["status"],
        "error_message": row["error_message"],
        "metadata": metadata,
        "source_file": row["source_file"] if "source_file" in row.keys() else "",
    }


def _row_to_lexicon(row: sqlite3.Row) -> dict[str, Any]:
    aliases = json.loads(row["aliases_json"]) if row["aliases_json"] else []
    evidence = (
        json.loads(row["evidence_refs_json"]) if row["evidence_refs_json"] else []
    )
    return {
        "id": row["id"],
        "source": row["source"],
        "target": row["target"],
        "aliases": aliases,
        "category": row["category"],
        "gender": row["gender"],
        "confidence": row["confidence"],
        "evidence_refs": evidence,
        "notes": row["notes"],
        "validated_by_user": bool(row["validated_by_user"]),
        "chapter_id": row["chapter_id"],
    }

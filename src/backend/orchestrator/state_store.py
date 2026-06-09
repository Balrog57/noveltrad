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
    metadata_json TEXT
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
        self._conn.executescript(SCHEMA_SQL)

        self._vector = None
        self._vector_import_error: str | None = None
        if self.vector_dir is not None:
            self._init_vector_store()

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
                    status, error_message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        limit: int | None = None,
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
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY chapter_id, chunk_index"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
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

    # ---------- diagnostics ----------

    def snapshot(self) -> dict[str, Any]:
        """Cheap summary used by GET /pipeline/state."""
        return {
            "chunks_total": self.count_chunks(),
            "chunks_by_status": {
                s: self.count_chunks(status=s)
                for s in (
                    "parsed",
                    "fast_translated",
                    "glossary_applied",
                    "consistency_checked",
                    "qa_checked",
                    "grammar_checked",
                    "polished",
                    "assembled",
                    "waiting_for_human",
                    "error",
                )
            },
            "lexicon_terms": self._scalar("SELECT COUNT(*) FROM lexicon_terms"),
            "qa_issues": self._scalar("SELECT COUNT(*) FROM qa_issues"),
            "grammar_issues": self._scalar("SELECT COUNT(*) FROM grammar_issues"),
            "consistency_flags": self._scalar(
                "SELECT COUNT(*) FROM consistency_flags"
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

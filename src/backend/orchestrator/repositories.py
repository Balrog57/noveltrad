"""Per-table repositories for StateStore.

Each repository wraps one logical table (chunks, lexicon_terms, qa_issues,
grammar_issues, consistency_flags, pending_hltl, pipeline_state) and exposes
a narrow CRUD surface. Repositories share the StateStore's single
``sqlite3.Connection`` and ``threading.RLock``; they never open their own.

Why split StateStore this way:
  * StateStore had grown to 44 methods on one class -- hard to navigate.
  * Each repository is now small (~50-150 lines) and tests can target one
    table in isolation.
  * StateStore becomes a thin facade that wires the repos and owns the
    connection lifecycle (open, close, transaction, migrations, vector).

API compatibility: StateStore keeps every public method that callers rely on
(see ``src/backend/routes/*``, ``src/backend/orchestrator/orchestrator.py``,
``src/backend/cli.py``). Each method is now a one-line delegate to the
matching repository method.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Row mappers
# ---------------------------------------------------------------------------


def row_to_chunk(row: sqlite3.Row) -> dict[str, Any]:
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
        "llm_refined": row["llm_refined"] if "llm_refined" in row.keys() else None,
        "qa_checked": row["qa_checked"],
        "grammar_checked": row["grammar_checked"],
        "polished_translation": row["polished_translation"],
        "status": row["status"],
        "error_message": row["error_message"],
        "metadata": metadata,
        "source_file": row["source_file"] if "source_file" in row.keys() else "",
        "review_score": row["review_score"] if "review_score" in row.keys() else None,
        "review_annotations": (
            json.loads(row["review_annotations"]) if row["review_annotations"] else None
        ),
    }


def row_to_lexicon(row: sqlite3.Row) -> dict[str, Any]:
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


def _project_created_sort_key(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class _Repo:
    """Common base: holds the shared connection + lock.

    Repositories never open their own SQLite connection. The StateStore owns
    the connection lifetime; the repos borrow it. All write paths take
    ``self._lock`` so concurrent FastAPI handlers cannot interleave with the
    orchestrator's drain loop.
    """

    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self._conn = conn
        self._lock = lock


# ---------------------------------------------------------------------------
# chunks
# ---------------------------------------------------------------------------


class ChunkRepo(_Repo):
    """CRUD on the ``chunks`` table."""

    def add(self, chunk: dict[str, Any]) -> None:
        meta = chunk.get("metadata") or {}
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO chunks (
                    id, chapter_id, chapter_title, chunk_index, source_text,
                    source_hash, glossary_version, output_hash,
                    raw_translation, glossary_applied, llm_refined, qa_checked,
                    grammar_checked, polished_translation,
                    status, error_message, metadata_json, source_file,
                    review_score, review_annotations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    chunk.get("llm_refined"),
                    chunk.get("qa_checked"),
                    chunk.get("grammar_checked"),
                    chunk.get("polished_translation"),
                    chunk.get("status", "parsed"),
                    chunk.get("error_message"),
                    json.dumps(meta, ensure_ascii=False) if meta else None,
                    chunk.get("source_file", ""),
                    chunk.get("review_score"),
                    json.dumps(chunk.get("review_annotations"), ensure_ascii=False)
                    if chunk.get("review_annotations")
                    else None,
                ),
            )

    def get(self, chunk_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM chunks WHERE id = ?", (chunk_id,)
            ).fetchone()
        return row_to_chunk(row) if row else None

    def update_field(self, chunk_id: str, field: str, value: Any) -> None:
        allowed = {
            "raw_translation",
            "glossary_applied",
            "llm_refined",
            "qa_checked",
            "grammar_checked",
            "polished_translation",
            "status",
            "error_message",
            "source_hash",
            "glossary_version",
            "output_hash",
            "review_score",
            "review_annotations",
            "metadata_json",
        }
        if field not in allowed:
            raise ValueError(f"Refusing to update non-allowlisted field: {field}")
        with self._lock:
            self._conn.execute(
                f"UPDATE chunks SET {field} = ? WHERE id = ?", (value, chunk_id)
            )

    def list(
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
        return [row_to_chunk(r) for r in rows]

    def count(self, status: str | None = None) -> int:
        with self._lock:
            if status is None:
                row = self._conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
            else:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS n FROM chunks WHERE status = ?", (status,)
                ).fetchone()
        return int(row["n"]) if row else 0


# ---------------------------------------------------------------------------
# lexicon_terms
# ---------------------------------------------------------------------------


class LexiconRepo(_Repo):
    """CRUD on the ``lexicon_terms`` table, including the merge upsert."""

    def add(self, term: dict[str, Any]) -> None:
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

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM lexicon_terms ORDER BY source"
            ).fetchall()
        return [row_to_lexicon(r) for r in rows]

    def find_by_source(self, source: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM lexicon_terms WHERE source = ?", (source,)
            ).fetchone()
        return row_to_lexicon(row) if row else None

    def upsert(self, term: dict[str, Any]) -> None:
        """Insert or update a lexicon term, merging by *source*.

        - If a term with the same *source* already exists, keep the higher
          confidence value, update the target if the new entry has higher
          confidence, and merge aliases/evidence_refs.
        - If no existing term, insert with a new UUID.
        """
        existing = self.find_by_source(term.get("source", ""))
        if existing is None:
            # New term -- generate id if missing
            if "id" not in term or not term["id"]:
                import uuid as _uuid

                term["id"] = _uuid.uuid4().hex[:12]
            self.add(term)
            return

        new_conf = float(term.get("confidence", 0.0))
        old_conf = float(existing.get("confidence", 0.0))

        if new_conf <= old_conf and term.get(
            "target", existing.get("target")
        ) == existing.get("target"):
            return

        updates: dict[str, Any] = {}
        if new_conf > old_conf:
            updates["confidence"] = new_conf
            updates["target"] = term.get("target", existing.get("target", ""))
            updates["category"] = term.get("category") or existing.get("category")
            updates["gender"] = term.get("gender") or existing.get("gender", "unknown")
            updates["notes"] = term.get("notes") or existing.get("notes")

        if updates:
            self.update(existing["id"], updates)

    def update(self, term_id: str, updates: dict[str, Any]) -> None:
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
        cols: list[str] = []
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

    def delete(self, term_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM lexicon_terms WHERE id = ?", (term_id,)
            )
            self._conn.commit()
            return cur.rowcount > 0


# ---------------------------------------------------------------------------
# qa_issues / grammar_issues / consistency_flags
# ---------------------------------------------------------------------------


class IssueRepo(_Repo):
    """Three small write/read surfaces for the chunk-level issue tables.

    They share one connection but are accessed through distinct helpers; this
    keeps the SQL local to one file and the public surface on StateStore
    identical to before.
    """

    def add_qa(self, issue: dict[str, Any]) -> None:
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

    def add_grammar(self, issue: dict[str, Any]) -> None:
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

    def add_consistency(self, flag: dict[str, Any]) -> None:
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

    def list_qa(self, chunk_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM qa_issues WHERE chunk_id = ? ORDER BY id", (chunk_id,)
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

    def list_grammar(self, chunk_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM grammar_issues WHERE chunk_id = ? ORDER BY id", (chunk_id,)
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

    def list_consistency(self, chunk_id: str) -> list[dict[str, Any]]:
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


# ---------------------------------------------------------------------------
# pending_hltl
# ---------------------------------------------------------------------------


class HltlRepo(_Repo):
    """The persistent HITL queue.

    ``register_hltl_record`` and ``resolve_hltl_record`` write; the rest are
    reads/clears. Records stay in the table after resolution so
    ``list_unresolved_hltl`` can be a true ``WHERE resolved_at IS NULL``.
    """

    def register(
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

    def resolve(self, request_id: str, resolved_at: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE pending_hltl SET resolved_at = ? WHERE request_id = ?",
                (resolved_at, request_id),
            )

    def list_unresolved(self) -> list[dict[str, Any]]:
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

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM pending_hltl")


# ---------------------------------------------------------------------------
# pipeline_state key/value + project records
# ---------------------------------------------------------------------------


class StateKV(_Repo):
    """The ``pipeline_state`` key/value table.

    Stores the active project pointer, the current project snapshot,
    artifact paths, and the loose ``project:<id>`` records. The fastAPI
    routes call into this for state polling; the orchestrator calls it
    during start/stop.
    """

    def set(self, key: str, value: Any) -> None:
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO pipeline_state (key, value) VALUES (?, ?)",
                (key, value),
            )

    def get(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM pipeline_state WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def get_json(self, key: str, default: Any = None) -> Any:
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    def delete(self, key: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM pipeline_state WHERE key = ?", (key,))


# ---------------------------------------------------------------------------
# projects (project metadata persisted under pipeline_state)
# ---------------------------------------------------------------------------


class ProjectRepo(_Repo):
    """Project metadata persisted as ``project:<id>`` rows in ``pipeline_state``.

    Kept separate from ``StateKV`` because project CRUD is non-trivial
    (parsing, defaulting, ordering, merge updates) and warrants its own
    surface.
    """

    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock, kv: StateKV):
        super().__init__(conn, lock)
        self._kv = kv

    def list(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, value FROM pipeline_state WHERE key LIKE 'project:%' "
                "AND key != 'project_manifest_path'",
            ).fetchall()
        projects: list[dict[str, Any]] = []
        for row in rows:
            try:
                data = json.loads(row["value"])
                project_id = row["key"].split(":", 1)[1]
                projects.append(
                    {
                        "project_id": project_id,
                        "name": data.get("name", f"Project-{project_id[:8]}"),
                        "source_path": data.get("source_path", ""),
                        "project_dir": data.get("project_dir", ""),
                        "source_lang": data.get("source_lang", ""),
                        "target_lang": data.get("target_lang", ""),
                        "profile": data.get("profile", "balanced"),
                        "output_format": data.get("output_format", "txt"),
                        "created_at": data.get("created_at", ""),
                    }
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                logger.warning(
                    "Skipping corrupt project record: %s", row["key"], exc_info=True
                )
        projects.sort(
            key=lambda project: _project_created_sort_key(project.get("created_at")),
            reverse=True,
        )
        return projects[offset : offset + limit]

    def get(self, project_id: str) -> dict[str, Any] | None:
        raw = self._kv.get(f"project:{project_id}")
        if raw is None:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Skipping corrupt project record: project:%s", project_id)
            return None
        return {
            "project_id": project_id,
            "name": data.get("name", f"Project-{project_id[:8]}"),
            "source_path": data.get("source_path", ""),
            "project_dir": data.get("project_dir", ""),
            "source_lang": data.get("source_lang", ""),
            "target_lang": data.get("target_lang", ""),
            "profile": data.get("profile", "balanced"),
            "output_format": data.get("output_format", "txt"),
            "created_at": data.get("created_at", ""),
        }

    def update(self, project_id: str, updates: dict[str, Any]) -> bool:
        existing = self.get(project_id)
        if existing is None:
            return False
        raw = self._kv.get(f"project:{project_id}")
        data = json.loads(raw) if raw else {}
        for key in ("name", "project_dir"):
            if key in updates and updates[key] is not None:
                data[key] = updates[key]
        self._kv.set(f"project:{project_id}", data)
        return True

    def delete(self, project_id: str) -> bool:
        existing = self.get(project_id)
        if existing is None:
            return False
        # Clear active project if it was this one
        if self.get_active() == project_id:
            self.clear_active()
        # Forget metadata
        self.forget(project_id)
        return True

    # ---- active project pointer ----

    def set_active(self, project_id: str) -> None:
        self._kv.set("active_project", project_id)

    def get_active(self) -> str | None:
        return self._kv.get("active_project")

    def clear_active(self) -> None:
        self._kv.delete("active_project")

    def forget(self, project_id: str) -> None:
        self._kv.delete(f"project:{project_id}")


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


class SnapshotReader(_Repo):
    """Cheap summary used by ``GET /pipeline/state``.

    Pulls chunk-by-status counts and a few scalar counts in a single
    read pass. Used by the FastAPI layer on every GUI poll, so it must
    stay cheap.
    """

    EXPECTED_STATUSES = (
        "parsed",
        "fast_translated",
        "lexicon_ready",
        "lexicon_skipped",
        "glossary_applied",
        "consistency_checked",
        "qa_checked",
        "grammar_checked",
        "reviewed",
        "polished",
        "assembled",
        "waiting_for_human",
        "error",
    )

    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock, vector_status: Callable[[], str]):
        super().__init__(conn, lock)
        self._vector_status = vector_status

    def build(self) -> dict[str, Any]:
        chunks_by_status = {s: 0 for s in self.EXPECTED_STATUSES}
        chunks_total = 0

        with self._lock:
            rows = self._conn.execute(
                "SELECT status, COUNT(*) as n FROM chunks GROUP BY status"
            ).fetchall()
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
            "vector_store": self._vector_status(),
        }

    def _scalar(self, sql: str) -> int:
        with self._lock:
            row = self._conn.execute(sql).fetchone()
        return int(row[0]) if row else 0

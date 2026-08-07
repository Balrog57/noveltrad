"""Translation persistence (SDD 8.6 segments, 8.7 snapshot serialization).

Segment rows are read/written exclusively by this repository; snapshot
serialization is canonical JSON of all PipelineSnapshot fields except
snapshot_hash (no API key).
"""

from __future__ import annotations

import json
import sqlite3

from noveltrad.core.clock import utc_now
from noveltrad.core.contracts import (
    DocumentId,
    PipelineSnapshot,
    ProviderName,
    SegmentId,
    SegmentState,
)

from .models import SegmentRow


def serialize_snapshot(snapshot: PipelineSnapshot) -> str:
    """Canonical JSON of all PipelineSnapshot fields except snapshot_hash."""
    provider = snapshot.provider
    provider_value = provider.value if hasattr(provider, "value") else str(provider)
    payload = {
        "provider": provider_value,
        "base_url": snapshot.base_url,
        "model": snapshot.model,
        "context_window_tokens": snapshot.context_window_tokens,
        "tokenizer_id": snapshot.tokenizer_id,
        "temperature": snapshot.temperature,
        "max_output_tokens": snapshot.max_output_tokens,
        "seed": snapshot.seed,
        "prompt_bundle_version": snapshot.prompt_bundle_version,
        "response_schema_version": snapshot.response_schema_version,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deserialize_snapshot(snapshot_json: str, snapshot_hash: str) -> PipelineSnapshot:
    """Rebuild the snapshot from canonical JSON plus its persisted hash."""
    payload = json.loads(snapshot_json)
    return PipelineSnapshot(
        provider=ProviderName(payload["provider"]),
        base_url=payload["base_url"],
        model=payload["model"],
        context_window_tokens=payload["context_window_tokens"],
        tokenizer_id=payload["tokenizer_id"],
        temperature=payload["temperature"],
        max_output_tokens=payload["max_output_tokens"],
        seed=payload["seed"],
        prompt_bundle_version=payload["prompt_bundle_version"],
        response_schema_version=payload["response_schema_version"],
        snapshot_hash=snapshot_hash,
    )


def snapshot_hash(snapshot: PipelineSnapshot) -> str:
    """SHA-256 of the canonical JSON, binding the snapshot (8.7)."""
    import hashlib

    return hashlib.sha256(serialize_snapshot(snapshot).encode("utf-8")).hexdigest()


class SegmentRepository:
    """Owns segment persistence; used by TranslationService only."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def count_for_document(self, document_id: DocumentId) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM segments WHERE chapter_id IN "
            "(SELECT id FROM chapters WHERE document_id=?)",
            (document_id,),
        ).fetchone()
        return int(row["c"])

    def insert_pending(
        self,
        chapter_id: int,
        order_index: int,
        source_start: int,
        source_end: int,
        source_hash: str,
    ) -> SegmentRow:
        now = utc_now().isoformat()
        cur = self._conn.execute(
            "INSERT INTO segments (chapter_id, order_index, source_start, source_end, "
            "source_hash, state, updated_at) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
            (chapter_id, order_index, source_start, source_end, source_hash, now),
        )
        return self.get(SegmentId(int(cur.lastrowid)))

    def get(self, segment_id: SegmentId) -> SegmentRow:
        row = self._conn.execute("SELECT * FROM segments WHERE id=?", (segment_id,)).fetchone()
        if row is None:
            raise KeyError(f"segment {segment_id} not found")
        return _to_row(row)

    def list_for_document(self, document_id: DocumentId) -> list[SegmentRow]:
        rows = self._conn.execute(
            "SELECT * FROM segments WHERE chapter_id IN "
            "(SELECT id FROM chapters WHERE document_id=?) "
            "ORDER BY chapter_id, order_index",
            (document_id,),
        ).fetchall()
        return [_to_row(r) for r in rows]

    def set_state(
        self,
        segment_id: SegmentId,
        state: SegmentState,
        checkpoint_path: str | None,
        checkpoint_hash: str | None,
    ) -> None:
        self._conn.execute(
            "UPDATE segments SET state=?, checkpoint_path=?, checkpoint_hash=?, "
            "retry_count=0, last_error=NULL, updated_at=? WHERE id=?",
            (str(state), checkpoint_path, checkpoint_hash, utc_now().isoformat(), segment_id),
        )

    def set_retry(self, segment_id: SegmentId, retry_count: int, safe_error: str) -> None:
        self._conn.execute(
            "UPDATE segments SET retry_count=?, last_error=?, updated_at=? WHERE id=?",
            (retry_count, safe_error, utc_now().isoformat(), segment_id),
        )

    def reset_document(self, document_id: DocumentId) -> None:
        self._conn.execute(
            "UPDATE segments SET state='PENDING', checkpoint_path=NULL, checkpoint_hash=NULL, "
            "retry_count=0, last_error=NULL, updated_at=? WHERE chapter_id IN "
            "(SELECT id FROM chapters WHERE document_id=?)",
            (utc_now().isoformat(), document_id),
        )


def _to_row(row: sqlite3.Row) -> SegmentRow:
    return SegmentRow(
        id=row["id"],
        chapter_id=row["chapter_id"],
        order_index=row["order_index"],
        source_start=row["source_start"],
        source_end=row["source_end"],
        source_hash=row["source_hash"],
        state=SegmentState(row["state"]),
        checkpoint_path=row["checkpoint_path"],
        checkpoint_hash=row["checkpoint_hash"],
        retry_count=row["retry_count"],
        last_error=row["last_error"],
        updated_at=row["updated_at"],
    )

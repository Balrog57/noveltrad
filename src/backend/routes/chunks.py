"""Chunk inspection + assemble + reprocess endpoints."""

from typing import Any

from fastapi import HTTPException

from .deps import Deps


def register(app: Any, deps: Deps) -> None:
    from .schemas import build_schemas

    AssembleRequest = build_schemas()["AssembleRequest"]

    @app.get("/chunks")
    def list_chunks(
        status: str | None = None,
        chapter_id: str | None = None,
        limit: int | None = 100,
        offset: int | None = 0,
    ) -> dict[str, Any]:
        items = deps.store.list_chunks(
            status=status, chapter_id=chapter_id, limit=limit, offset=offset
        )
        total = deps.store.count_chunks(status=status)
        return {
            "items": items,
            "chunks": items,  # legacy key for the Files tab
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/chunks/{chunk_id}")
    def get_chunk(chunk_id: str) -> dict[str, Any]:
        chunk = deps.store.get_chunk(chunk_id)
        if chunk is None:
            raise HTTPException(status_code=404, detail="chunk not found")
        chunk["qa_issues"] = deps.store.list_qa_issues(chunk_id)
        chunk["grammar_issues"] = deps.store.list_grammar_issues(chunk_id)
        chunk["consistency_flags"] = deps.store.list_consistency_flags(chunk_id)
        return chunk

    @app.post("/pipeline/replay-chunks")
    def replay_chunks(body: dict[str, Any]) -> dict[str, Any]:
        chunk_ids = body.get("chunk_ids") or []
        if not isinstance(chunk_ids, list):
            raise HTTPException(status_code=422, detail="chunk_ids must be a list")
        replayed = deps.orchestrator.replay_chunks(chunk_ids)
        return {"replayed": replayed}

    @app.post("/assemble")
    def assemble(req: AssembleRequest) -> dict[str, Any]:
        return deps.orchestrator.assemble_now(req.output_path, fmt=req.format)

    @app.post("/chunks/{chunk_id}/reprocess")
    def reprocess_chunk(chunk_id: str) -> dict[str, Any]:
        chunk = deps.store.get_chunk(chunk_id)
        if chunk is None:
            raise HTTPException(status_code=404, detail="chunk not found")
        from src.backend.agents.base_worker import make_task_message

        try:
            queues = deps.orchestrator._workers.queues_for("fast_translator")  # type: ignore[attr-defined]
        except KeyError:
            raise HTTPException(status_code=503, detail="translator not running")
        queues.input.put(
            make_task_message(
                chunk_id=chunk_id,
                action="translate",
                payload={
                    "source_text": chunk.get("source_text", ""),
                    "chapter_id": chunk.get("chapter_id"),
                    "chapter_title": chunk.get("chapter_title"),
                },
            )
        )
        deps.store.update_chunk_field(chunk_id, "status", "parsed")
        return {"status": "queued", "chunk_id": chunk_id}


__all__ = ["register"]

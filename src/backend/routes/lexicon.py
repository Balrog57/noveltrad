"""Lexicon CRUD + import/export endpoints."""

import logging
import uuid
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from .deps import Deps
from .schemas import build_schemas

logger = logging.getLogger(__name__)


def register(app: Any, deps: Deps) -> None:
    schemas = build_schemas()
    LexiconTermCreate = schemas["LexiconTermCreate"]

    @app.get("/lexicon")
    def list_lexicon() -> dict[str, Any]:
        return {"terms": deps.store.list_lexicon()}

    @app.post("/lexicon")
    def create_lexicon_term(req: LexiconTermCreate) -> dict[str, Any]:  # type: ignore[valid-type]
        term_id = uuid.uuid4().hex[:12]
        deps.store.add_lexicon_term(
            {
                "id": term_id,
                "source": req.source,
                "target": req.target,
                "aliases": req.aliases or [],
                "category": req.category,
                "gender": req.gender,
                "confidence": req.confidence,
                "notes": req.notes,
                "validated_by_user": req.validated_by_user,
                "chapter_id": req.chapter_id,
                "evidence_refs": [],
            }
        )
        return {"id": term_id, "status": "created"}

    @app.put("/lexicon/{term_id}")
    def update_lexicon_term(term_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        deps.store.update_lexicon_term(term_id, updates)
        return {"ok": True}

    @app.delete("/lexicon/{term_id}")
    def delete_lexicon_term(term_id: str) -> dict[str, Any]:
        deleted = deps.store.delete_lexicon_term(term_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Term not found")
        return {"ok": True, "term_id": term_id}

    @app.get("/lexicon/export")
    def export_lexicon() -> Any:
        return JSONResponse(content={"terms": deps.store.list_lexicon()})

    @app.post("/lexicon/import")
    def import_lexicon(payload: dict[str, Any]) -> dict[str, Any]:
        terms = payload.get("terms") or []
        for t in terms:
            if isinstance(t, dict) and "source" in t and "target" in t:
                t.setdefault("id", uuid.uuid4().hex[:12])
                try:
                    deps.store.add_lexicon_term(t)
                except Exception:
                    logger.exception("lexicon import: failed to add term")
        return {"imported": len(terms)}


__all__ = ["register"]

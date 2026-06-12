"""Human-in-the-loop (HITL) endpoints."""

from typing import Any

from fastapi import HTTPException

from .deps import Deps


def register(app: Any, deps: Deps) -> None:
    from .schemas import build_schemas

    HITLResponseRequest = build_schemas()["HITLResponseRequest"]

    @app.get("/hltl/pending")
    def hltl_pending() -> dict[str, Any]:
        return {"requests": deps.orchestrator.pending_hltl()}

    @app.post("/hltl/respond")
    def hltl_respond(req: HITLResponseRequest) -> dict[str, Any]:
        ok = deps.orchestrator.respond_hltl(req.request_id, req.answer)
        if not ok:
            raise HTTPException(status_code=404, detail="request not found")
        return {"ok": True}

    @app.post("/orchestrator/hltl/replay")
    def hltl_replay() -> dict[str, Any]:
        """Re-inject every waiting-for-human chunk that has a live target worker."""
        return deps.orchestrator.replay_pending_hltl()


__all__ = ["register"]

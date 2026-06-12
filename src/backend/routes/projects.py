"""Project lifecycle + pipeline control + chunk submission endpoints."""

import uuid
from pathlib import Path
from typing import Any

from src.backend.orchestrator.orchestrator import ProjectContext

from .deps import Deps


def register(app: Any, deps: Deps) -> None:
    from .schemas import build_schemas

    schemas = build_schemas()
    ProjectCreateRequest = schemas["ProjectCreateRequest"]
    ProjectStateResponse = schemas["ProjectStateResponse"]
    PipelineStateResponse = schemas["PipelineStateResponse"]
    ChunkSubmitRequest = schemas["ChunkSubmitRequest"]
    ReplayChunksRequest = schemas["ReplayChunksRequest"]

    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        items = deps.store.list_projects()
        return {"projects": items}

    @app.post("/projects")
    def create_project(req: ProjectCreateRequest) -> dict[str, Any]:
        project_id = req.project_id or uuid.uuid4().hex[:12]
        ctx = _build_context(project_id, req)
        _persist_project_metadata(deps, project_id, ctx)
        if req.parse:
            _kickoff_parser(deps, project_id, ctx)
        return {"project_id": project_id, "status": "created"}

    @app.post("/pipeline/start")
    def pipeline_start(req: ProjectCreateRequest) -> dict[str, Any]:
        project_id = req.project_id or uuid.uuid4().hex[:12]
        ctx = _build_context(project_id, req)
        deps.orchestrator.start(ctx)
        return {"project_id": project_id, "status": "running"}

    @app.post("/pipeline/pause")
    def pipeline_pause() -> dict[str, Any]:
        deps.orchestrator.pause()
        return {"status": "paused"}

    @app.post("/pipeline/resume")
    def pipeline_resume() -> dict[str, Any]:
        deps.orchestrator.resume()
        return {"status": "running"}

    @app.post("/pipeline/stop")
    def pipeline_stop() -> dict[str, Any]:
        deps.orchestrator.stop()
        return {"status": "stopped"}

    @app.get("/pipeline/state", response_model=PipelineStateResponse)
    def pipeline_state() -> PipelineStateResponse:
        snap = deps.orchestrator.snapshot()
        proj = snap["project"]
        return PipelineStateResponse(
            project=(ProjectStateResponse(**proj) if proj is not None else None),
            state_store=snap["state_store"],
            workers=snap["workers"],
            paused_stages=snap["paused_stages"],
            pending_hltl=snap["pending_hltl"],
            event_log_tail=snap["event_log_tail"],
            output_artifact=snap.get("output_artifact"),
            project_manifest_path=snap.get("project_manifest_path"),
        )

    @app.post("/chunks/submit")
    def chunks_submit(req: ChunkSubmitRequest) -> dict[str, Any]:
        count = deps.orchestrator.submit_chunks(req.chunks)
        return {"submitted": count}

    @app.post("/pipeline/replay-chunks")
    def replay_chunks(req: ReplayChunksRequest) -> dict[str, Any]:
        count = deps.orchestrator.replay_chunks(req.chunk_ids)
        return {"replayed": count, "chunk_ids": req.chunk_ids}


def _build_context(project_id: str, req: Any) -> ProjectContext:
    return ProjectContext(
        project_id=project_id,
        project_dir=Path(req.project_dir),
        source_path=Path(req.source_path),
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        output_path=Path(req.output_path) if req.output_path else None,
        profile=req.profile,
        output_format=req.output_format,
    )


def _persist_project_metadata(deps: Deps, project_id: str, ctx: ProjectContext) -> None:
    deps.store.set_state(
        f"project:{project_id}",
        {
            "project_dir": str(ctx.project_dir),
            "source_path": str(ctx.source_path),
            "source_lang": ctx.source_lang,
            "target_lang": ctx.target_lang,
            "output_path": str(ctx.output_path) if ctx.output_path else None,
            "created_at": ctx.started_at,
            "profile": ctx.profile,
            "output_format": ctx.output_format,
        },
    )


def _kickoff_parser(deps: Deps, project_id: str, ctx: ProjectContext) -> None:
    from src.backend.agents.base_worker import make_task_message

    deps.orchestrator.start(ctx)
    parser_q = deps.orchestrator._workers.queues_for("parser").input  # type: ignore[attr-defined]
    parser_q.put(
        make_task_message(
            chunk_id=project_id,
            action="parse",
            payload={
                "project_id": project_id,
                "project_dir": str(ctx.project_dir),
                "source_path": str(ctx.source_path),
                "source_lang": ctx.source_lang,
                "target_lang": ctx.target_lang,
                "output_path": str(ctx.output_path) if ctx.output_path else None,
            },
        )
    )


__all__ = ["register"]

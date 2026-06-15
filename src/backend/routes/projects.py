"""Project lifecycle + pipeline control + chunk submission endpoints."""

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from src.backend.orchestrator.orchestrator import ProjectContext

from .deps import Deps


def register(app: Any, deps: Deps) -> None:
    from .schemas import build_schemas

    schemas = build_schemas()
    ProjectCreateRequest = schemas["ProjectCreateRequest"]
    ProjectUpdateRequest = schemas["ProjectUpdateRequest"]
    ProjectStateResponse = schemas["ProjectStateResponse"]
    PipelineStateResponse = schemas["PipelineStateResponse"]
    ProjectQueueEntry = schemas["ProjectQueueEntry"]
    ChunkSubmitRequest = schemas["ChunkSubmitRequest"]
    ReplayChunksRequest = schemas["ReplayChunksRequest"]

    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        items = deps.store.list_projects()
        return {"projects": items}

    @app.get("/projects/active")
    def get_active_project() -> dict[str, Any]:
        active_id = deps.store.get_active_project()
        if active_id is None:
            return {"active_project_id": None, "project": None}
        proj = deps.store.get_project(active_id)
        return {"active_project_id": active_id, "project": proj}

    @app.get("/projects/{project_id}")
    def get_project(project_id: str) -> dict[str, Any]:
        proj = deps.store.get_project(project_id)
        if proj is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return proj

    @app.put("/projects/{project_id}")
    def update_project(project_id: str, req: ProjectUpdateRequest) -> dict[str, Any]:
        updates = {}
        if req.name is not None:
            updates["name"] = req.name
        if req.project_dir is not None:
            updates["project_dir"] = req.project_dir
        ok = deps.store.update_project(project_id, updates)
        if not ok:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"ok": True, "project_id": project_id}

    @app.delete("/projects/{project_id}")
    def delete_project(project_id: str) -> dict[str, Any]:
        ok = deps.store.delete_project(project_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"ok": True, "project_id": project_id}

    @app.post("/projects/{project_id}/activate")
    def activate_project(project_id: str) -> dict[str, Any]:
        proj = deps.store.get_project(project_id)
        if proj is None:
            raise HTTPException(status_code=404, detail="Project not found")
        deps.store.set_active_project(project_id)
        return {"ok": True, "active_project_id": project_id, "project": proj}

    @app.post("/projects")
    def create_project(req: ProjectCreateRequest) -> dict[str, Any]:
        project_id = req.project_id or uuid.uuid4().hex[:12]
        # Normalise to a list: ``source_paths`` wins if non-empty,
        # otherwise we treat ``source_path`` as a single-element list
        # for back-compat with older clients.
        paths: list[str] = []
        if req.source_paths:
            paths = [str(p) for p in req.source_paths if p]
        elif req.source_path:
            paths = [str(req.source_path)]
        ctx = _build_context(project_id, req, source_paths=paths)
        # Inject the human-readable name into the context for persistence.
        if req.name:
            ctx.name = req.name  # type: ignore[attr-defined]
        _persist_project_metadata(deps, project_id, ctx)
        # If no source files provided, just create the project (empty).
        if not paths or not req.parse:
            deps.store.set_active_project(project_id)
            return {
                "project_id": project_id,
                "status": "created",
                "queue_position": 0,
                "source_paths": paths,
            }
        started = _kickoff_parser(deps, project_id, ctx, paths)
        with deps.orchestrator._lock:
            qpos = (
                deps.orchestrator._project_queue.index(ctx) + 1
                if ctx in deps.orchestrator._project_queue
                else 0
            )
        return {
            "project_id": project_id,
            "status": "queued" if not started else "running",
            "queue_position": qpos,
            "source_paths": paths,
        }

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
            project_queue=[
                ProjectQueueEntry(**q) for q in snap.get("project_queue", [])
            ],
            project_queue_size=snap.get("project_queue_size", 0),
        )

    @app.post("/chunks/submit")
    def chunks_submit(req: ChunkSubmitRequest) -> dict[str, Any]:
        count = deps.orchestrator.submit_chunks(req.chunks)
        return {"submitted": count}

    @app.post("/pipeline/replay-chunks")
    def replay_chunks(req: ReplayChunksRequest) -> dict[str, Any]:
        count = deps.orchestrator.replay_chunks(req.chunk_ids)
        return {"replayed": count, "chunk_ids": req.chunk_ids}

    @app.delete("/projects/{project_id}/queue")
    def remove_queued_project(project_id: str) -> dict[str, Any]:
        """Drop a queued (not-yet-running) project from the FIFO.

        Returns 409 if the project is the one currently running.
        """
        with deps.orchestrator._lock:
            current = deps.orchestrator._project
            if current is not None and current.project_id == project_id:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot remove the running project; stop the pipeline first.",
                )
        removed = deps.orchestrator.remove_queued_project(project_id)
        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"No queued project with id {project_id!r}.",
            )
        return {"ok": True, "project_id": project_id}

    @app.delete("/projects/{project_id}/local-data")
    def clear_project_local_data(project_id: str) -> dict[str, Any]:
        project = deps.store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        removed, skipped = _remove_project_local_files(project)
        current = deps.store.get_state_json("current_project", default={}) or {}
        if current.get("project_id") == project_id:
            deps.store.clear_project_data()
            removed.append("sqlite:current_project_pipeline_rows")
        deps.store.forget_project(project_id)
        removed.append("sqlite:project_metadata")
        return {
            "ok": True,
            "project_id": project_id,
            "removed": removed,
            "skipped": skipped,
        }


def _build_context(
    project_id: str, req: Any, source_paths: list[str] | None = None
) -> ProjectContext:
    paths = source_paths or ([req.source_path] if req.source_path else [])
    return ProjectContext(
        project_id=project_id,
        project_dir=Path(req.project_dir),
        source_path=Path(paths[0]) if paths else None,
        source_paths=[Path(p) for p in paths],
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
            "name": getattr(ctx, "name", None) or f"Project-{project_id[:8]}",
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


def _kickoff_parser(
    deps: Deps, project_id: str, ctx: ProjectContext, source_paths: list[str]
) -> bool:
    """Start the pipeline and queue the parser task.

    The orchestrator's ``start()`` is now the single entry point:
    it spawns the workers, spawns the parser task and emits
    ``pipeline_started``. If a project is already running, the
    call enqueues and the parser is kicked off later by
    ``_start_next_queued_project``.

    Returns ``True`` if the pipeline started immediately,
    ``False`` if the project was queued.
    """
    with deps.orchestrator._lock:
        was_idle = deps.orchestrator._project is None
    deps.orchestrator.start(ctx)
    with deps.orchestrator._lock:
        queued = ctx in deps.orchestrator._project_queue
    return was_idle and not queued


def _remove_project_local_files(project: dict[str, Any]) -> tuple[list[str], list[str]]:
    removed: list[str] = []
    skipped: list[str] = []
    project_dir_raw = project.get("project_dir") or ""
    if not project_dir_raw:
        return removed, ["project_dir:missing"]
    try:
        project_root = Path(project_dir_raw).expanduser().resolve()
    except OSError:
        return removed, [f"project_dir:invalid:{project_dir_raw}"]
    if not project_root.exists():
        return removed, [f"project_dir:not_found:{project_root}"]

    candidates = [
        project_root / ".noveltrad_vectors",
        project_root / ".noveltrad_llm_cache",
        project_root / ".llm_cache",
        project_root / ".noveltrad_state.db",
        project_root / ".noveltrad_state.db-shm",
        project_root / ".noveltrad_state.db-wal",
    ]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            skipped.append(str(candidate))
            continue
        if not _is_relative_to(resolved, project_root):
            skipped.append(f"outside_project:{resolved}")
            continue
        if not resolved.exists():
            continue
        if resolved.is_dir():
            shutil.rmtree(resolved)
        else:
            resolved.unlink()
        removed.append(str(resolved))
    return removed, skipped


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


__all__ = ["register"]

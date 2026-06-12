"""FastAPI backend server — entry point for the v4 multi-agent pipeline.

Run:
    python src/backend/server.py --port 8000

This module is the GUI-free entrypoint. It owns:
  * the StateStore (single writer)
  * the Orchestrator
  * the FastAPI app (REST + WebSocket)

Import-order note (AGENTS.md): onnxruntime/ctranslate2 must be imported
BEFORE PyQt6 to avoid Windows DLL conflicts. The backend itself doesn't
import PyQt6, so the canonical import block is only relevant for the
GUI entrypoint (src/main_qt.py). We still import heavy native deps
(uvicorn, fastapi) lazily where reasonable.
"""

import argparse
import logging
import os
import sys
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Ensure src/ is importable when launched as `python src/backend/server.py`.
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from src.backend.orchestrator.orchestrator import Orchestrator, ProjectContext
from src.backend.orchestrator.state_store import StateStore

logger = logging.getLogger("noveltrad.backend")


def _frozen_debug_log(message: str) -> None:
    if not getattr(sys, "frozen", False):
        return
    try:
        path = (
            Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
            / "NovelTrad"
            / "backend.log"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception:
        pass


# ---------- FastAPI app factory ----------


def _build_schemas() -> dict[str, Any]:
    from pydantic import BaseModel, Field

    class ProjectCreateRequest(BaseModel):
        project_id: str | None = None
        project_dir: str
        source_path: str
        source_lang: str = "auto"
        target_lang: str = "fr"
        output_path: str | None = None
        output_format: str = Field(default="txt", pattern=r"^(epub|epub_bilingual|docx|srt|txt)$")
        parse: bool = True
        profile: str = Field(default="balanced", pattern=r"^(eco|balanced|premium)$")

    class ProjectStateResponse(BaseModel):
        project_id: str
        status: str
        source_lang: str
        target_lang: str
        started_at: float

    class PipelineStateResponse(BaseModel):
        project: ProjectStateResponse | None
        state_store: dict[str, Any]
        workers: dict[str, Any]
        paused_stages: list[str]
        pending_hltl: int
        event_log_tail: list[dict[str, Any]]
        output_artifact: dict[str, Any] | None = None
        project_manifest_path: str | None = None

    class HITLResponseRequest(BaseModel):
        request_id: str
        answer: str = Field(..., min_length=1)

    class ChunkSubmitRequest(BaseModel):
        chunks: list[dict[str, Any]]

    class AssembleRequest(BaseModel):
        output_path: str
        format: str = "txt"

    class LexiconTermCreate(BaseModel):
        source: str
        target: str
        aliases: list[str] | None = None
        category: str | None = None
        gender: str = "unknown"
        confidence: float = 0.5
        notes: str | None = None
        validated_by_user: bool = False
        chapter_id: str | None = None

    class ReplayChunksRequest(BaseModel):
        chunk_ids: list[str] = Field(..., min_length=1)

    return {
        "ProjectCreateRequest": ProjectCreateRequest,
        "ProjectStateResponse": ProjectStateResponse,
        "PipelineStateResponse": PipelineStateResponse,
        "HITLResponseRequest": HITLResponseRequest,
        "ChunkSubmitRequest": ChunkSubmitRequest,
        "AssembleRequest": AssembleRequest,
        "LexiconTermCreate": LexiconTermCreate,
        "ReplayChunksRequest": ReplayChunksRequest,
    }


def create_app(
    db_path: str | Path | None = None,
    vector_dir: str | Path | None = None,
) -> "Any":
    """Build the FastAPI app.

    The heavy imports (fastapi, uvicorn) are deferred so that simply
    importing this module from a test or from the GUI process doesn't
    require the web stack to be installed (it normally will be, but
    we keep the option open).
    """
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware

    schemas = _build_schemas()
    ProjectCreateRequest = schemas["ProjectCreateRequest"]
    ProjectStateResponse = schemas["ProjectStateResponse"]
    PipelineStateResponse = schemas["PipelineStateResponse"]
    HITLResponseRequest = schemas["HITLResponseRequest"]
    ChunkSubmitRequest = schemas["ChunkSubmitRequest"]
    AssembleRequest = schemas["AssembleRequest"]
    LexiconTermCreate = schemas["LexiconTermCreate"]
    ReplayChunksRequest = schemas["ReplayChunksRequest"]

    if db_path is None:
        db_path = Path(os.environ.get("NOVELTRAD_DB", "./.noveltrad_state.db"))
    if vector_dir is None:
        vector_dir = Path(
            os.environ.get("NOVELTRAD_VECTORS", "./.noveltrad_vectors")
        )

    store = StateStore(db_path=db_path, vector_dir=vector_dir)
    orchestrator = Orchestrator(store)

    @asynccontextmanager
    async def lifespan(app: "Any"):
        logger.info(
            "NovelTrad backend starting (db=%s, vectors=%s)",
            db_path,
            store.vector_status,
        )
        try:
            yield
        finally:
            logger.info("NovelTrad backend shutting down")
            orchestrator.shutdown()
            store.close()

    from src.backend import __version__ as _backend_version

    app = FastAPI(
        title="NovelTrad Backend",
        version=_backend_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----- REST routes -----

    @app.get("/health")
    def health() -> dict[str, Any]:
        from src.backend.engines.nllb_engine import diagnostics as nllb_diagnostics
        from src.backend.llm_router.router import get_router

        provider_count = 0
        try:
            router = get_router()
            provider_count = len(router.providers)
            llm_stats = router.stats()
            llm_ready = bool(router.providers) or os.environ.get("NOVELTRAD_FAKE_LLM") in {
                "1",
                "true",
                "yes",
            }
        except Exception as exc:
            llm_stats = {"error": str(exc)}
            llm_ready = False
        return {
            "ok": True,
            "version": _backend_version,
            "vector_store": store.vector_status,
            "nllb": nllb_diagnostics(),
            "llm": {
                "ready": llm_ready,
                "provider_count": provider_count,
                "stats": llm_stats,
                "mode": getattr(router, "mode", "offline") if llm_ready else "offline",
                "usage": router.usage() if llm_ready else {},
            },
        }

    @app.get("/usage")
    def usage() -> dict[str, Any]:
        from src.backend.llm_router.router import get_router

        try:
            router = get_router()
            return {
                "mode": router.mode,
                **router.usage(),
            }
        except Exception as exc:
            return {"mode": "offline", "error": str(exc)}

    @app.get("/llm/providers")
    def llm_providers(
        ollama_base_url: str = "http://127.0.0.1:11434",
    ) -> dict[str, Any]:
        """Discovery endpoint used by the first-run wizard and settings tab.

        Returns:
          * ``ollama``: a discovery payload (reachable, version, models,
            error) probed against ``ollama_base_url``. The GUI uses it
            to populate a model picker.
          * ``ollama_suggestions``: curated local models the user can
            install with one click (display only — installation is done
            via the Ollama CLI in a future story; today the user types
            the name).
          * ``cloud_suggestions``: curated OpenAI-compatible endpoints
            the user can pick from a list.
          * ``providers``: the providers currently registered in the
            running router (derived from the config + env).
          * ``defaults``: the ``ConfigManager`` defaults so the GUI can
            fall back to known-good values.

        The endpoint never raises; every failure mode is captured in
        the returned ``ollama.error`` field.
        """
        from src.backend.llm_router.router import (
            SUGGESTED_CLOUD_MODELS,
            SUGGESTED_OLLAMA_MODELS,
            discover_ollama_models,
            get_router,
        )

        discovery = discover_ollama_models(ollama_base_url)
        try:
            router = get_router()
            providers = [
                {
                    "name": p.name,
                    "kind": p.kind,
                    "base_url": p.base_url,
                    "model": p.model,
                }
                for p in router.providers
            ]
        except Exception as exc:  # noqa: BLE001
            providers = [{"error": str(exc)}]

        return {
            "ollama": {
                "reachable": bool(discovery.get("reachable")),
                "base_url": discovery.get("base_url"),
                "version": discovery.get("version"),
                "error": discovery.get("error"),
                "models": [
                    {
                        "name": m.name,
                        "size_bytes": m.size_bytes,
                        "family": m.family,
                        "parameter_size": m.parameter_size,
                        "quantization": m.quantization,
                        "modified_at": m.modified_at,
                    }
                    for m in (discovery.get("models") or [])
                ],
            },
            "ollama_suggestions": list(SUGGESTED_OLLAMA_MODELS),
            "cloud_suggestions": list(SUGGESTED_CLOUD_MODELS),
            "providers": providers,
            "defaults": {
                "provider": "ollama",
                "model": "gemma3:4b",
                "base_url": "http://127.0.0.1:11434",
            },
        }

    @app.post("/llm/providers/refresh")
    def llm_providers_refresh() -> dict[str, Any]:
        """Re-probe Ollama and rebuild the router providers from env.

        Called by the GUI's 'Re-detect' button. Returns the same shape
        as ``GET /llm/providers``.
        """
        from src.backend.llm_router.router import (
            SUGGESTED_CLOUD_MODELS,
            SUGGESTED_OLLAMA_MODELS,
            discover_ollama_models,
            get_router,
        )

        try:
            router = get_router()
            router.providers.clear()
            router._circuits.clear()  # type: ignore[attr-defined]
            router._provider_locks.clear()  # type: ignore[attr-defined]
            router.default_providers_from_env()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

        base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        discovery = discover_ollama_models(base)
        return {
            "ok": True,
            "ollama": {
                "reachable": bool(discovery.get("reachable")),
                "base_url": discovery.get("base_url"),
                "version": discovery.get("version"),
                "error": discovery.get("error"),
                "models": [
                    {"name": m.name, "size_bytes": m.size_bytes}
                    for m in (discovery.get("models") or [])
                ],
            },
            "ollama_suggestions": list(SUGGESTED_OLLAMA_MODELS),
            "cloud_suggestions": list(SUGGESTED_CLOUD_MODELS),
            "provider_count": len(router.providers),
        }

    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        items = store.list_projects()
        return {"projects": items}

    @app.post("/projects")
    def create_project(req: ProjectCreateRequest) -> dict[str, Any]:
        project_id = req.project_id or uuid.uuid4().hex[:12]
        ctx = ProjectContext(
            project_id=project_id,
            project_dir=Path(req.project_dir),
            source_path=Path(req.source_path),
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            output_path=Path(req.output_path) if req.output_path else None,
            profile=req.profile,
            output_format=req.output_format,
        )
        store.set_state(
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
        if req.parse:
            orchestrator.start(ctx)
            from .agents.base_worker import make_task_message

            parser_q = orchestrator._workers.queues_for("parser").input  # type: ignore[attr-defined]
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
        return {"project_id": project_id, "status": "created"}

    @app.post("/pipeline/start")
    def pipeline_start(req: ProjectCreateRequest) -> dict[str, Any]:
        project_id = req.project_id or uuid.uuid4().hex[:12]
        ctx = ProjectContext(
            project_id=project_id,
            project_dir=Path(req.project_dir),
            source_path=Path(req.source_path),
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            output_path=Path(req.output_path) if req.output_path else None,
            profile=req.profile,
            output_format=req.output_format,
        )
        orchestrator.start(ctx)
        return {"project_id": project_id, "status": "running"}

    @app.post("/pipeline/pause")
    def pipeline_pause() -> dict[str, Any]:
        orchestrator.pause()
        return {"status": "paused"}

    @app.post("/pipeline/resume")
    def pipeline_resume() -> dict[str, Any]:
        orchestrator.resume()
        return {"status": "running"}

    @app.post("/pipeline/stop")
    def pipeline_stop() -> dict[str, Any]:
        orchestrator.stop()
        return {"status": "stopped"}

    @app.get("/pipeline/state", response_model=PipelineStateResponse)
    def pipeline_state() -> PipelineStateResponse:
        snap = orchestrator.snapshot()
        proj = snap["project"]
        return PipelineStateResponse(
            project=(
                ProjectStateResponse(**proj) if proj is not None else None
            ),
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
        count = orchestrator.submit_chunks(req.chunks)
        return {"submitted": count}

    @app.get("/chunks")
    def list_chunks(
        status: str | None = None,
        chapter_id: str | None = None,
        limit: int | None = 100,
        offset: int | None = 0,
    ) -> dict[str, Any]:
        items = store.list_chunks(
            status=status, chapter_id=chapter_id, limit=limit, offset=offset
        )
        total = store.count_chunks(status=status)
        return {
            "items": items,
            "chunks": items,  # legacy key for the Files tab
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/chunks/{chunk_id}")
    def get_chunk(chunk_id: str) -> dict[str, Any]:
        chunk = store.get_chunk(chunk_id)
        if chunk is None:
            raise HTTPException(status_code=404, detail="chunk not found")
        chunk["qa_issues"] = store.list_qa_issues(chunk_id)
        chunk["grammar_issues"] = store.list_grammar_issues(chunk_id)
        chunk["consistency_flags"] = store.list_consistency_flags(chunk_id)
        return chunk

    @app.post("/assemble")
    def assemble(req: AssembleRequest) -> dict[str, Any]:
        result = orchestrator.assemble_now(req.output_path, fmt=req.format)
        return result

    @app.post("/chunks/{chunk_id}/reprocess")
    def reprocess_chunk(chunk_id: str) -> dict[str, Any]:
        chunk = store.get_chunk(chunk_id)
        if chunk is None:
            raise HTTPException(status_code=404, detail="chunk not found")
        from .agents.base_worker import make_task_message

        try:
            queues = orchestrator._workers.queues_for("fast_translator")  # type: ignore[attr-defined]
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
        store.update_chunk_field(chunk_id, "status", "parsed")
        return {"status": "queued", "chunk_id": chunk_id}

    @app.post("/pipeline/replay-chunks")
    def replay_chunks(req: ReplayChunksRequest) -> dict[str, Any]:
        count = orchestrator.replay_chunks(req.chunk_ids)
        return {"replayed": count, "chunk_ids": req.chunk_ids}

    @app.get("/lexicon")
    def list_lexicon() -> dict[str, Any]:
        return {"terms": store.list_lexicon()}

    @app.post("/lexicon")
    def create_lexicon_term(req: LexiconTermCreate) -> dict[str, Any]:
        import uuid as _uuid

        term_id = _uuid.uuid4().hex[:12]
        store.add_lexicon_term(
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
        store.update_lexicon_term(term_id, updates)
        return {"ok": True}

    @app.delete("/lexicon/{term_id}")
    def delete_lexicon_term(term_id: str) -> dict[str, Any]:
        deleted = store.delete_lexicon_term(term_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Term not found")
        return {"ok": True, "term_id": term_id}

    @app.get("/lexicon/export")
    def export_lexicon() -> dict[str, Any]:
        from fastapi.responses import JSONResponse

        return JSONResponse(content={"terms": store.list_lexicon()})

    @app.post("/lexicon/import")
    def import_lexicon(payload: dict[str, Any]) -> dict[str, Any]:
        terms = payload.get("terms") or []
        for t in terms:
            if isinstance(t, dict) and "source" in t and "target" in t:
                import uuid as _uuid

                t.setdefault("id", _uuid.uuid4().hex[:12])
                try:
                    store.add_lexicon_term(t)
                except Exception:
                    logger.exception("lexicon import: failed to add term")
        return {"imported": len(terms)}

    @app.get("/hltl/pending")
    def hltl_pending() -> dict[str, Any]:
        return {"requests": orchestrator.pending_hltl()}

    @app.post("/hltl/respond")
    def hltl_respond(req: HITLResponseRequest) -> dict[str, Any]:
        ok = orchestrator.respond_hltl(req.request_id, req.answer)
        if not ok:
            raise HTTPException(status_code=404, detail="request not found")
        return {"ok": True}

    @app.post("/orchestrator/hltl/replay")
    def hltl_replay() -> dict[str, Any]:
        """Re-inject every waiting-for-human chunk that has a live target worker.

        Returns a summary so the GUI can show a status toast.
        """
        return orchestrator.replay_pending_hltl()

    # ----- WebSocket -----

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        def push(event: dict[str, Any]) -> None:
            # WebSocket fan-out is async; we schedule the send on the
            # running loop using a thread-safe primitive (FastAPI's
            # Starlette WebSocket). We use `run_coroutine_threadsafe`
            # via the running loop captured at connection time.
            try:
                loop = websocket.app.state._ws_loop  # type: ignore[attr-defined]
            except AttributeError:
                loop = None
            if loop is None or loop.is_closed():
                return
            import asyncio

            asyncio.run_coroutine_threadsafe(
                _safe_send(websocket, event), loop
            )

        async def _safe_send(ws: WebSocket, payload: dict[str, Any]) -> None:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

        websocket.app.state._ws_loop = (
            __import__("asyncio").get_event_loop()
        )
        orchestrator.add_listener(push)
        try:
            while True:
                # Drain incoming pings; the GUI uses this to stay
                # connected and we use it to detect disconnect.
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        finally:
            orchestrator.remove_listener(push)

    return app


# ---------- CLI entrypoint ----------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="noveltrad-backend")
    parser.add_argument("--host", default=os.environ.get("NOVELTRAD_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("NOVELTRAD_PORT", "8765")))
    parser.add_argument(
        "--db",
        "--db-path",
        dest="db",
        default=None,
        help="Path to SQLite state DB",
    )
    parser.add_argument(
        "--vectors", default=None, help="Path to LanceDB vector directory"
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    _frozen_debug_log("server.main: before create_app")
    app = create_app(db_path=args.db, vector_dir=args.vectors)
    _frozen_debug_log("server.main: after create_app")

    try:
        _frozen_debug_log("server.main: before import uvicorn")
        import uvicorn
        _frozen_debug_log("server.main: after import uvicorn")
    except ImportError:
        print(
            "uvicorn is required to run the backend. Install it with:\n"
            "    pip install uvicorn[standard] fastapi",
            file=sys.stderr,
        )
        return 1

    _frozen_debug_log("server.main: before uvicorn.run")
    run_kwargs = {
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level.lower(),
    }
    if getattr(sys, "frozen", False):
        run_kwargs["log_config"] = None
        run_kwargs["access_log"] = False
    uvicorn.run(app, **run_kwargs)
    _frozen_debug_log("server.main: after uvicorn.run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""FastAPI backend server — entry point for the v4 multi-agent pipeline.

Run:
    python src/backend/server.py --port 8000

This module is the GUI-free entrypoint. It owns:
  * the StateStore (single writer)
  * the Orchestrator
  * the FastAPI app (REST + WebSocket)

The actual route handlers live under :mod:`src.backend.routes`.
``create_app`` is a thin assembler that builds the shared ``Deps``
container and asks each module to register its endpoints on the
FastAPI app instance.

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
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Ensure src/ is importable when launched as `python src/backend/server.py`.
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from src.backend.orchestrator.orchestrator import Orchestrator
from src.backend.orchestrator.state_store import StateStore
from src.backend.routes import Deps
from src.backend.routes import chunks as chunks_routes
from src.backend.routes import health as health_routes
from src.backend.routes import hltl as hltl_routes
from src.backend.routes import lexicon as lexicon_routes
from src.backend.routes import llm as llm_routes
from src.backend.routes import projects as projects_routes
from src.backend.routes import ws as ws_routes

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
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    # Load user config (NLLB_MODEL, OLLAMA_MODEL, etc.) into env
    try:
        from src.gui.app_config import ConfigManager
        ConfigManager().apply_environment()
    except Exception:
        pass

    if db_path is None:
        db_path = Path(os.environ.get("NOVELTRAD_DB", "./.noveltrad_state.db"))
    if vector_dir is None:
        vector_dir = Path(
            os.environ.get("NOVELTRAD_VECTORS", "./.noveltrad_vectors")
        )

    store = StateStore(db_path=db_path, vector_dir=vector_dir)
    orchestrator = Orchestrator(store)
    deps = Deps(store=store, orchestrator=orchestrator)

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
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (
        health_routes,
        llm_routes,
        projects_routes,
        chunks_routes,
        lexicon_routes,
        hltl_routes,
        ws_routes,
    ):
        module.register(app, deps)

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

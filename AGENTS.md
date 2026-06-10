# AGENTS.md

Guidance for AI coding agents working in this repository. Keep it repo-specific
and verify before changing assumptions.

## What This Is

NovelTrad v4 is a PyQt6 desktop translation app backed by a FastAPI
multi-agent pipeline for novels and web novels.

Supported source formats in the v4 backend: EPUB, DOCX, TXT, SRT.
Primary engines: NLLB via ctranslate2 for fast local translation, and an
OpenAI-compatible/Ollama LLM router for lexicon, QA, polishing, and review
steps. Ollama calls are serialized by default to avoid overloading local
hardware.

## Entry Points And Layout

- Desktop entrypoint: `src/main_qt.py` (also re-launches the backend in-process
  via `src/main_qt.py --backend ...` when the GUI starts it).
- Backend-only entrypoint: `python -m src.backend.server`.
- Active source layout:
  - `src/backend/` — FastAPI server, orchestrator, agents, engines, formats,
    LLM router. Must stay GUI-free (no PyQt6 imports).
  - `src/gui/` — minimal PyQt6 v4 client (4 tabs + dialogs/widgets).
  - `tests/` — unittest-based smoke tests.
- Previous CAT/TM modules are intentionally removed. Do not reintroduce
  root-level `src/core`, `src/engines`, `src/formats`, or `src/utils`.

## Commands

- Install dev/runtime deps: `pip install -r requirements.txt`
- Run desktop app: `python src/main_qt.py`
- Run backend only: `python -m src.backend.server --host 127.0.0.1 --port 8765`
- Compile check used by CI: `python -m compileall src`
- Run the unit/smoke tests: `python -m unittest discover tests`
  (most tests are fast; the multiprocessing backend smoke in
  `tests/test_backend_smoke.py` is gated on `NOVELTRAD_RUN_SLOW_SMOKE=1`).
- Standalone build: `python build_script.py` (uses `build.spec`, writes
  `dist/NovelTrad/NovelTrad.exe`).
- Installer: compile `NovelTrad.iss` with Inno Setup 6.

## Things Agents Frequently Get Wrong Here

- Import order in `src/main_qt.py` matters: `onnxruntime` and `ctranslate2`
  are imported (best-effort, in `try/except ImportError`) **before** `PyQt6`
  to avoid Windows DLL conflicts. Preserve this order in any Qt entrypoint.
  The backend (`src/backend/`) does not import PyQt6, so this is only
  relevant for the GUI side.
- `argostranslate`, `deep-translator`, and the old v3 engines are not part of
  the v4 app. Do not add them back unless a new feature explicitly needs them.
- The GUI is intentionally small: `MainWindow`, four tabs (`translate`,
  `settings`, `glossaries`, `files`), `ActivityLog`, `HITLPopup`, and
  `ChunkDetailDialog`. There is also a `FirstRunWizard`.
- `ConfigManager` lives in `src/gui/app_config.py`. User config is stored at
  `%APPDATA%/NovelTrad/config.json`; the legacy `config.json` at the repo
  root is only a migration fallback. The backend reads env-equivalents via
  `ConfigManager().apply_environment()`.
- Use `statusBar()` as the Qt method; do not introduce a `status_bar`
  attribute. See `src/gui/main_window.py`.
- Pipeline state belongs in SQLite files created per run/project (e.g.
  `.smoke.db` for the smoke test, `.noveltrad_state.db` for the default),
  not in tracked repository files. LanceDB vector state lives under
  `.noveltrad_vectors/`. Both are local-only.
- The frozen-build backend writes a debug log to
  `%APPDATA%/NovelTrad/backend.log`; the GUI entrypoint writes
  `backend_debug` traces when launched from a PyInstaller bundle. Don't
  remove the `getattr(sys, "frozen", False)` guards.

## Backend Quirks

- `src/backend/server.py` exposes both a FastAPI `app = create_app(...)` and
  a CLI `main(argv)`. Tests use `fastapi.testclient.TestClient(create_app(...))`
  with `db_path=` and `vector_dir=` overrides; pass a `tempfile.TemporaryDirectory`
  path so the test does not touch the real `.noveltrad_state.db`.
- Environment knobs used by tests/fakes:
  `NOVELTRAD_TRANSLATION_TEST_MODE=1` and `NOVELTRAD_FAKE_LLM=1` switch on
  offline fakes; `NOVELTRAD_HOST` / `NOVELTRAD_PORT` override defaults.
- The orchestrator publishes events to listeners; the WebSocket endpoint in
  `create_app` registers itself as a listener via `orchestrator.add_listener`.
  Don't confuse this with pydantic event models.

## Local-Only Agent Files

`tasks/todo.md` and `tasks/lessons.md` are local-only planning files
(ignored by Git). Update them when the local agent setup asks for it.

`OmegaT_Doc/`, `.kilo/`, virtual environments, build artifacts (`build/`,
`dist/`), local projects, sample documents, and smoke-test SQLite files
are local-only. Never publish their contents.

## Validation Before Declaring Done

For non-trivial changes, run at minimum:

1. `python -m compileall src`
2. `python -m unittest discover tests` (fast tests)
3. `python -m src.backend.server --db-path .smoke.db` and check `GET /health`
4. `python src/main_qt.py` and confirm the window launches

For pipeline changes, also create or submit a small source file and confirm
the activity log (WebSocket) receives progress events.

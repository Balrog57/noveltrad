# AGENTS.md

Repo-specific guidance for AI coding agents. Keep it short. Every line should
answer "would an agent likely miss this without help?" If not, leave it out.

## What This Is

NovelTrad v4 is a PyQt6 desktop translation app backed by a FastAPI
multi-agent pipeline for novels and web novels.

- Supported source formats (v4 backend): EPUB, DOCX, TXT, SRT.
- Primary engines: NLLB via `ctranslate2` for fast local translation; an
  OpenAI-compatible / Ollama LLM router for lexicon, QA, polishing, and
  review (Ollama calls are serialized by default to avoid overloading
  local hardware).
- Previous CAT/TM modules are intentionally removed. Do not reintroduce
  root-level `src/core`, `src/engines`, `src/formats`, or `src/utils`.

## Entry Points And Layout

- Desktop GUI: `src/main_qt.py`. On launch the GUI spawns the backend as a
  subprocess (`MainWindow._start_backend` in `src/gui/main_window.py`).
- Headless backend: `python -m src.backend.server` (also `python
  src/backend/server.py`). The same entrypoint doubles as a CLI
  (`--host`, `--port`, `--db`/`--db-path`, `--vectors`, `--log-level`).
- Headless CLI for translation/management: `python -m src.backend.cli`
  (subcommands: `translate`, `project`, `pipeline`, `glossary`, `chunk`,
  `hltl`, `batch`, `server`, `health`, `config`). Default mode uses
  FastAPI `TestClient`; `--remote` connects to an already-running backend.
- `python src/main_qt.py --backend ...` runs the backend in the *same*
  process (frozen-build launch path; not what the GUI does normally).
- `src/backend/` must stay GUI-free (no PyQt6 imports).
- `src/gui/` is a small PyQt6 client: `MainWindow` (sidebar + stacked
  pages, 5 entries: Translate, Projects, Glossaries, Files, Settings),
  `ActivityLog`, `HITLPopup`, `ChunkDetailDialog`, `UpdateDialog`,
  `ProjectDialog`, `FirstRunWizard`, and the `tabs/`, `dialogs/`,
  `widgets/` subpackages.
- `src/backend/agents/`: parser, fast_translator, lexicon_builder,
  glossary_applier, consistency_checker, qa_validator, grammar_proofer,
  llm_polisher, llm_refiner, reviewer, terminology_researcher, assembler,
  plus `base_worker.py` and `prompt_contracts.py`.

## Commands

- Install runtime/dev deps: `pip install -r requirements.txt`
  (CI does `pip install -e .` first and falls back to requirements.txt).
- Run desktop app: `python src/main_qt.py`
- Run backend only: `python -m src.backend.server --host 127.0.0.1 --port 8765`
- Compile check (CI): `python -m compileall src`
- Run the test suite: `python -m unittest discover tests` (most tests are
  fast; `tests/test_backend_smoke.py` and `tests/test_headless_client.py`
  are gated on `NOVELTRAD_RUN_SLOW_SMOKE=1`).
- Health probe (after starting the backend): `curl http://127.0.0.1:8765/health`
- Build: `python build.py --all` (chains wheel + PyInstaller bundle +
  Inno Setup installer). `build_script.py` is a backward-compat shim
  equivalent to `python build.py --all`; prefer `build.py` for new code.
  Stage the build with `python build.py --wheel | --exe | --installer`.
- Installer: compile `NovelTrad.iss` with **Inno Setup 6**. `build.py`
  auto-locates `ISCC.exe` under
  `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` or
  `C:\Program Files*\Inno Setup 6\ISCC.exe`.
- PyInstaller bundle lands at `dist\NovelTrad\NovelTrad.exe` with a
  sibling `VERSION` file (used by the auto-updater).

## Versioning Rule (enforced by tests)

`src.__version__` is the single source of truth. It must match:

- `version` in `pyproject.toml`
- `src/backend.__version__` (re-exported from `src.__version__`)

`tests/test_health_version.py` asserts all three agree and that
`GET /health` returns that version. When bumping, edit only
`src/__init__.py` — `build.py` reads it via `import src`.

## Things Agents Frequently Get Wrong Here

- **Import order in `src/main_qt.py`**: `onnxruntime` and `ctranslate2`
  are imported in `try/except ImportError` **before** `PyQt6` to avoid
  Windows DLL conflicts (msvcp140, zlib). Keep this order in any Qt
  entrypoint. The backend (`src/backend/`) does not import PyQt6, so
  this only matters on the GUI side.
- **`argostranslate`, `deep-translator`, and the old v3 engines are not
  part of v4.** Don't add them back unless a new feature explicitly
  needs them.
- **Use `statusBar()` as the Qt method** (called 21+ times in
  `src/gui/main_window.py`). Do not introduce a `status_bar` attribute.
- **`ConfigManager`** lives in `src/gui/app_config.py`. User config is
  stored at `%APPDATA%\NovelTrad\config.json`; the legacy
  `config.json` at the repo root is only a migration fallback. The
  backend reads env-equivalents via
  `ConfigManager().apply_environment()`.
- **Pipeline state** lives in per-run / per-project SQLite files
  (`.noveltrad_state.db` for the default, `.smoke.db` for the smoke
  test). LanceDB vector state goes under `.noveltrad_vectors/`. Both
  are local-only and listed in `.gitignore`.
- **Frozen-build debug logs** are written to
  `%APPDATA%\NovelTrad\backend.log` by `MainWindow._start_backend` and
  `src/backend/server._frozen_debug_log`. Don't remove the
  `getattr(sys, "frozen", False)` guards.
- **i18n switching needs a restart**: Qt only honours the launch-time
  language; the Settings combobox persists the choice to `ConfigManager`
  but the next launch picks it up. `pylrelease6`/`lrelease` is only
  required when `NOVELTRAD_REQUIRE_QM=1`.

## Backend Quirks (for test/work-on-backend tasks)

- `src/backend/server.py` exposes both `create_app(db_path, vector_dir)`
  (used by tests) and a CLI `main(argv)`. The CLI flag is `--db` or
  `--db-path`; the Python kwarg is `db_path=`. Tests pass
  `tempfile.TemporaryDirectory()` paths so they don't touch
  `.noveltrad_state.db` on disk.
- Env knobs: `NOVELTRAD_FAKE_LLM=1` and
  `NOVELTRAD_TRANSLATION_TEST_MODE=1` switch on offline fakes;
  `NOVELTRAD_HOST` / `NOVELTRAD_PORT` override defaults;
  `NOVELTRAD_VERSION` overrides the runtime version (CI sets it from
  `github.ref_name`).
- The orchestrator publishes events to listeners; the WebSocket route
  in `create_app` registers itself via `orchestrator.add_listener`.
  Don't confuse this with pydantic event models.

## Local-Only / Ignored Files

`tasks/todo.md`, `tasks/lessons.md`, `OmegaT_Doc/`, `.kilo/`, virtual
environments (`.venv*`), build artefacts (`build/`, `dist/`), local
projects, sample documents, and smoke-test SQLite files are all
local-only and listed in `.gitignore`. Do not publish their contents.

The PyInstaller bundle includes `assets/noveltrad-icon.ico` and
`assets/noveltrad-logo-256.png` (see `build.spec` `datas` block). Don't
rename them without updating the spec.

## Validation Before Declaring Done

For non-trivial changes, run at minimum:

1. `python -m compileall src`
2. `python -m unittest discover tests` (fast tests; skip the
   `NOVELTRAD_RUN_SLOW_SMOKE=1` ones unless you specifically need them)
3. `python -m src.backend.server --db-path .smoke.db` and check
   `GET /health` returns `{"ok": true, "version": "<src.__version__>"}`
4. `python src/main_qt.py` and confirm the window launches

For pipeline changes, also submit a small source file and confirm the
Activity log (WebSocket) receives progress events.

## Release Process (when cutting a new version)

See `docs/RELEASING.md` for the full flow. TL;DR:

1. Bump `__version__` in `src/__init__.py` only — `pyproject.toml` is
   not edited by hand; `build.py` reads the version from
   `src.__version__`.
2. Tag the commit: `git tag vX.Y.Z && git push --tags`.
3. `.github/workflows/release.yml` builds wheel + bundle + installer on
   `windows-latest` and opens a **draft** GitHub release.
4. Pre-release tags (`v4.0.0-rc1`, etc.) are intentionally ignored by
   the workflow — use a branch for that.
5. Optional Authenticode code-signing: see `docs/SIGNING.md`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

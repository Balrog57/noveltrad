# NovelTrad

NovelTrad is a **PyQt6 desktop application** for translating long-form
fiction and web novels. A local **FastAPI** backend drives a
**multi-agent pipeline** that ingests a text-like document, chunks it,
runs specialised agents for fast translation, lexicon building,
glossary application, consistency checks, QA, grammar proofing, LLM
polishing, and finally assembles a translated artefact.

> The active architecture is **v4**. Earlier CAT/TM modules have been
> removed from the source tree; this document only describes v4.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Install](#install)
- [Run](#run)
- [Configuration](#configuration)
- [Build a Windows installer](#build-a-windows-installer)
- [Release process](#release-process)
- [Validation](#validation)
- [Auto-updates](#auto-updates)
- [Project-local notes](#project-local-notes)

---

## Features

- **Multi-agent translation pipeline** orchestrated by a multiprocessing
  worker pool with a SQLite state store, crash-safe HITL, and a
  back-pressure-aware queue (see `src/backend/orchestrator/`).
- **9 specialised agent stages**: parser, fast translator, lexicon
  builder, glossary applier, consistency checker, QA validator, grammar
  proofer, LLM polisher, assembler
  (`src/backend/agents/`).
- **Local-first translation engine**: NLLB via `ctranslate2` for fast
  batch translation, plus an Ollama / OpenAI-compatible LLM router
  for the lexicon, QA, polishing, and review steps
  (`src/backend/engines/`, `src/backend/llm_router/`).
- **Document readers and chunker** for EPUB, DOCX, TXT, and SRT
  (`src/backend/formats/`).
- **PyQt6 GUI** with a responsive sidebar + stacked-pages layout,
  a design system / theme manager, a 3-step translate workflow
  (drop → review → run), and a separate Files / Glossaries / Settings
  page. A "Recent projects" page is wired in as a placeholder.
- **WebSocket activity log**, chunk detail dialog, and HITL popup
  for human-in-the-loop corrections.
- **Auto-updater** based on GitHub Releases: `Settings → Check for
  updates` compares `tag_name` to the running version and verifies
  the SHA256 of the downloaded installer.
- **Standalone Windows build** with PyInstaller; Inno Setup produces
  a signed installer (see `docs/SIGNING.md`).

---

## Architecture

```text
PyQt6 desktop client (src/gui)
  - Sidebar + stacked pages: Translate, Projects (placeholder),
    Glossaries, Files, Settings
  - Activity log over WebSocket
  - HITL popup, chunk detail dialog, update dialog
  - First-run wizard, theme manager, design system
  - HTTP/WebSocket client (src/gui/backend_client.py)

FastAPI backend (src/backend)
  - SQLite StateStore (per-run / per-project)
  - multiprocessing WorkerManager
  - 9-agent pipeline (parser → fast translator → lexicon → glossary
    → consistency → QA → grammar → polisher → assembler)
  - NLLB engine via ctranslate2
  - Ollama / OpenAI-compatible LLM router (serialized by default
    to avoid overloading local hardware)
  - Optional LanceDB vector store under .noveltrad_vectors/
```

The backend can run independently from the UI. The UI starts it
automatically when launched from `src/main_qt.py`, or it can be run
directly for API testing.

---

## Repository layout

```text
src/
  __init__.py              # __version__ (single source of truth)
  main_qt.py               # Desktop entrypoint (imports onnxruntime/
                           # ctranslate2 *before* PyQt6 to avoid
                           # Windows DLL conflicts)
  backend/
    server.py              # FastAPI app + CLI (create_app / main)
    orchestrator/
      orchestrator.py      # Event publication, listener fan-out
      pipeline.py          # Stage definitions, ordering, retries
      state_store.py       # SQLite-backed run state
      worker_manager.py    # multiprocessing worker pool
    agents/                # parser, fast_translator, lexicon_builder,
                           # glossary_applier, consistency_checker,
                           # qa_validator, grammar_proofer,
                           # llm_polisher, assembler
    engines/
      nllb_engine.py       # ctranslate2 wrapper
    formats/
      __init__.py          # EPUB / DOCX / TXT / SRT readers + chunker
    llm_router/
      router.py            # Ollama + OpenAI-compatible routing/cache
  gui/
    app_config.py          # ConfigManager (v4 JSON config)
    main_window.py         # Sidebar + 5-page stacked shell
    backend_client.py      # HTTP/WebSocket client
    design_system.py       # Tokens, components, themes
    first_run_wizard.py    # First-run configuration wizard
    updater.py             # GitHub Releases auto-updater
    tabs/                  # translate, settings, glossaries, files
    dialogs/               # chunk_detail, hitl_popup, update_dialog
    widgets/               # activity_log, event_debouncer

docs/
  RELEASING.md             # Cutting a new release with build.py + CI
  SIGNING.md               # Optional Authenticode code-signing

build.py                   # Build entrypoint (wheel / exe / installer)
build_script.py            # Backward-compat shim → build.py --all
build.spec                 # PyInstaller spec
NovelTrad.iss              # Inno Setup script (SignTool macro)
pyproject.toml             # Package metadata, version
requirements.txt           # Runtime + packaging deps
.github/workflows/
  ci.yml                   # Lint + test on every push / PR
  release.yml              # Build + draft release on vX.Y.Z tag
tests/                     # unittest-based smoke tests
```

The previous CAT/TM modules (`src/core`, `src/engines`, `src/formats`,
`src/utils` at the repo root) are intentionally removed. Do not
reintroduce them.

---

## Install

```powershell
git clone https://github.com/Balrog57/noveltrad.git
cd noveltrad
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional local model setup (the LLM router speaks Ollama):

```powershell
ollama pull gemma3:4b
```

Supported Python: **3.10+**. CI runs on Windows with **3.11** and
**3.12**.

---

## Run

Desktop app (the GUI launches the backend in-process if it is not
already running):

```powershell
python src/main_qt.py
```

Backend only (useful for API testing or headless runs):

```powershell
python -m src.backend.server --host 127.0.0.1 --port 8765
```

Health check:

```powershell
curl http://127.0.0.1:8765/health
```

Environment knobs for offline / CI runs:

| Variable                              | Effect                                                            |
| ------------------------------------- | ----------------------------------------------------------------- |
| `NOVELTRAD_FAKE_LLM=1`                | Use the in-process fake LLM (no Ollama / OpenAI calls).          |
| `NOVELTRAD_TRANSLATION_TEST_MODE=1`   | Use the offline translation stub.                                 |
| `NOVELTRAD_HOST`, `NOVELTRAD_PORT`    | Override the default backend bind address / port.                 |
| `NOVELTRAD_VERSION`                   | Override the runtime version (CI uses this from `github.ref_name`).|

---

## Configuration

User configuration is stored at:

```text
%APPDATA%\NovelTrad\config.json
```

A legacy `config.json` at the repo root is used as a migration
fallback only. The backend reads env-equivalents via
`ConfigManager().apply_environment()` (`src/gui/app_config.py`).

Pipeline state is **per run / per project**:

```text
.noveltrad_state.db       # SQLite (WAL) — one file per run/project
.noveltrad_vectors/       # LanceDB vector state (optional)
```

Both are local-only and listed in `.gitignore`.

---

## Build a Windows installer

```powershell
# Full pipeline: sdist + wheel + PyInstaller bundle + Inno Setup installer
python build.py --all

# Individual stages
python build.py --wheel
python build.py --exe
python build.py --installer
```

The PyInstaller bundle is written to `dist/NovelTrad/NovelTrad.exe`.
The Inno Setup installer lands at
`dist/Setup_NovelTrad-vX.Y.Z.exe`. Compile `NovelTrad.iss` manually
with **Inno Setup 6** if you only want the installer:

```powershell
& "C:\Inno Setup 6\ISCC.exe" NovelTrad.iss
```

`build_script.py` is kept as a backward-compatible shim
(`python build_script.py` ≡ `python build.py --all`) for older CI
recipes and muscle memory. Prefer `build.py` for new code.

For optional Authenticode code-signing, see `docs/SIGNING.md`.

---

## Release process

The release flow is documented in detail in
[`docs/RELEASING.md`](docs/RELEASING.md). TL;DR:

1. Bump `__version__` in `src/__init__.py` **and** the `version` field
   in `pyproject.toml` (both must match).
2. Tag the commit: `git tag vX.Y.Z && git push --tags`.
3. `.github/workflows/release.yml` builds the wheel + bundle +
   installer, computes the SHA256, writes `latest.json`, and opens
   a **draft** GitHub release with the artefacts attached.
4. Review the release notes in the GitHub UI, then publish.

Pre-release tags (`v4.0.0-rc1`, etc.) are ignored by the workflow
on purpose; use a branch for that.

---

## Validation

Quick local checks (mirrors what CI runs):

```powershell
python -m compileall src
$env:NOVELTRAD_FAKE_LLM = "1"
$env:NOVELTRAD_TRANSLATION_TEST_MODE = "1"
python -m unittest discover -s tests -p "test_*.py"

# Smoke-test the backend in isolation
python -m src.backend.server --db-path .smoke.db
# In another shell:
curl http://127.0.0.1:8765/health
```

Manual end-to-end smoke test:

1. Launch the desktop app: `python src/main_qt.py`.
2. Drop a small EPUB, DOCX, TXT, or SRT file on the Translate tab.
3. Walk through the 3-step workflow (select engine & glossary,
   review chunks, run the pipeline).
4. Confirm the **Activity log** receives backend events over the
   WebSocket.
5. Open the **Files** tab and inspect chunk details.
6. Trigger a HITL popup from a chunk with low QA confidence and
   verify the corrected text flows back into the pipeline.

---

## Auto-updates

`src/gui/updater.py` ships a Sparkle-like updater that talks to the
GitHub Releases API:

1. Three seconds after startup, it calls
   `https://api.github.com/repos/Balrog57/noveltrad/releases/latest`.
2. It parses `tag_name` with `packaging.version` and compares it to
   the running `__version__`.
3. When a newer release is found, the **UpdateDialog** shows the
   release notes and a *Update now* button.
4. The installer is downloaded from the `download_url` in
   `latest.json`, its **SHA256** is verified against the manifest,
   and Inno Setup is launched via `ShellExecuteW`
   (`os.startfile`).

Signatures are **not** verified by the updater in v4; SHA256 over HTTPS
is the trust boundary. See `docs/SIGNING.md` for optional Authenticode
signing of the installer.

---

## Project-local notes

`tasks/todo.md`, `tasks/lessons.md`, `OmegaT_Doc/`, `.kilo/`, the
virtual environments, build artefacts (`build/`, `dist/`), local
projects, sample documents, and smoke-test SQLite files are all
**local-only** and ignored by Git. They must not be published.

If you are an AI coding agent working in this repository, read
[`AGENTS.md`](AGENTS.md) first — it lists the layout, the validation
recipe, and the recurring mistakes to avoid.

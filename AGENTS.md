# AGENTS.md

Guidance for AI coding agents working in this repository. Keep it repo-specific
and verify before changing assumptions.

## What This Is

NovelTrad v4 is a PyQt6 desktop translation app backed by a FastAPI
multi-agent pipeline for novels and web novels.

Supported source formats in the v4 backend: EPUB, DOCX, TXT, SRT.
Primary engines: NLLB via ctranslate2 for fast local translation, and an
OpenAI-compatible/Ollama LLM router for lexicon, QA, polishing, and review
steps.

## Entry Points And Layout

- Desktop entrypoint: `src/main_qt.py`.
- Backend-only entrypoint: `python -m src.backend.server`.
- Active source layout:
  - `src/backend/` — FastAPI server, orchestrator, agents, engines, formats.
  - `src/gui/` — minimal PyQt6 v4 client.
- Previous CAT/TM modules are intentionally removed. Do not reintroduce
  root-level `src/core`, `src/engines`, `src/formats`, or `src/utils`.

## Commands

- Install dev/runtime deps: `pip install -r requirements.txt`
- Run desktop app: `python src/main_qt.py`
- Run backend only: `python -m src.backend.server --host 127.0.0.1 --port 8765`
- Compile check used by CI: `python -m compileall src`
- Standalone build: `python build_script.py`
- Installer: compile `NovelTrad.iss` with Inno Setup 6.

## Things Agents Frequently Get Wrong Here

- Import order in `src/main_qt.py` matters: optional runtime libraries such as
  `onnxruntime` and `ctranslate2` are imported before `PyQt6` to avoid Windows
  DLL conflicts. Preserve this order in any Qt entrypoint.
- `argostranslate`, `deep-translator`, and the old v3 engines are not part of
  the v4 app. Do not add them back unless a new feature explicitly needs them.
- The GUI is intentionally small: `MainWindow`, four tabs, `ActivityLog`,
  `HITLPopup`, and `ChunkDetailDialog`.
- The backend must stay GUI-free. `src/backend/...` must not import PyQt6.
- `ConfigManager` now lives in `src/gui/app_config.py`.
- Use `statusBar()` as the Qt method; do not create a `status_bar` attribute.
- The pipeline state belongs in SQLite files created per run/project, not in
  tracked repository files.

## Local-Only Agent Files

`.agents/rules/rules.md` may require updating `tasks/todo.md` and
`tasks/lessons.md`. Those paths are ignored by Git and local-only, but update
them when the local agent setup asks for it.

`OmegaT_Doc/`, `.kilo/`, `.agents/`, virtual environments, and sample
projects are local-only. Never publish their contents.

## Validation Before Declaring Done

For non-trivial changes, run at minimum:

1. `python -m compileall src`
2. `python -m src.backend.server --db-path .smoke.db` and check `/health`
3. `python src/main_qt.py` and confirm the window launches

For pipeline changes, also create or submit a small source file and confirm the
activity log receives progress events.

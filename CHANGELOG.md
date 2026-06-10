# Changelog

All notable changes to **NovelTrad** are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> The current public architecture is **v4**. Pre-v4 entries are kept
> for historical context but no v3 source code is shipped in this
> repository.

---

## [Unreleased]

### Added
- LLM auto-discovery: the first-run wizard and settings tab now call
  `GET /llm/providers` and `POST /llm/providers/refresh` to
  enumerate the local Ollama models, suggest curated local models
  (gemma3:4b, llama3.1:8b, qwen2.5:7b, phi4:14b, mistral-nemo:12b)
  and curated OpenAI-compatible cloud endpoints
  (gpt-4o-mini, gpt-4o, claude-3-5-sonnet, gemini-1.5-flash,
  deepseek-chat). The user can still type a custom model and base
  URL.

### Planned
- Real "Recent projects" page (currently a placeholder in the GUI).
- HMAC-signed `latest.json` for stronger auto-update integrity.
- Optional Authenticode verification step in the auto-updater
  (see `docs/SIGNING.md`).

---

## [4.0.0] — 2026-06-10

The first public v4 release. Rewrote both halves of the application
around a multi-agent translation pipeline and a minimal PyQt6 shell.

### Added
- **Multi-agent translation pipeline** (orchestrator + worker pool):
  - 9 specialised agent stages: parser, fast translator, lexicon
    builder, glossary applier, consistency checker, QA validator,
    grammar proofer, LLM polisher, assembler.
  - SQLite-backed `StateStore`, multiprocessing `WorkerManager`,
    crash-safe HITL, run-level event channel, drainable back-pressure
    queue.
- **FastAPI backend** (`src/backend/server.py`) with a `create_app()`
  factory and a CLI entrypoint (`python -m src.backend.server`).
- **NLLB engine** via `ctranslate2` for fast local batch translation.
- **Ollama / OpenAI-compatible LLM router** with on-disk caching;
  Ollama calls are serialised by default to avoid overloading local
  hardware.
- **Document readers and chunker** for EPUB, DOCX, TXT, and SRT.
- **PyQt6 desktop client** with a responsive sidebar + 5-page
  stacked layout (Translate, Projects placeholder, Glossaries, Files,
  Settings), a 3-step translate workflow, a design system / theme
  manager, a first-run wizard, an activity log over WebSocket, a
  chunk detail dialog, and a HITL popup.
- **Auto-updater** (`src/gui/updater.py`) reading
  `https://api.github.com/repos/Balrog57/noveltrad/releases/latest`,
  comparing `tag_name` to the running version with
  `packaging.version`, and verifying the SHA256 of the downloaded
  installer against a `latest.json` manifest.
- **Standalone Windows build** with PyInstaller (`build.spec`) and an
  Inno Setup 6 installer (`NovelTrad.iss`) with an optional
  Authenticode `SignTool` macro.
- **CI workflows**:
  - `ci.yml` — Windows + Python 3.11 / 3.12, compileall + unittest
    on every push and pull request.
  - `release.yml` — triggered on `vX.Y.Z` tags; builds wheel +
    PyInstaller bundle + installer, computes the SHA256, writes
    `latest.json`, uploads artefacts, and opens a **draft** GitHub
    release.
- **Unittest-based smoke tests** under `tests/`, runnable offline
  with `NOVELTRAD_FAKE_LLM=1` and
  `NOVELTRAD_TRANSLATION_TEST_MODE=1`.

### Changed
- Rewrote `README.md` around the multi-agent workflow.
- Replaced the placeholder `LICENSE` notice with an MIT reference.
- Refactored the build pipeline into a `build.py` entrypoint with
  `--wheel`, `--exe`, `--installer`, and `--all` modes.
  `build_script.py` is kept as a backward-compatible shim
  (`python build_script.py` ≡ `python build.py --all`).

### Removed
- All v3 CAT/TM modules (`src/core`, `src/engines`, `src/formats`,
  `src/utils` at the repo root) and the v3 regression test suite.
- Stale `OmegaT_Doc/` reference material and the OmegaT submodule.
- Local planning files (`tasks/todo.md`, `tasks/lessons.md`,
  `OmegaT_Doc/`, `.kilo/`, venvs, build artefacts, local projects,
  sample documents, smoke-test SQLite files) from version control.

---

## Earlier versions (pre-v4, historical)

The pre-v4 line of NovelTrad was a CAT/TM-style tool with a different
codebase (OmegaT-like alignment tools, `tmx2source`, `vcs_manager`,
OmegaT-compliant `last_entry.properties`, etc.). The v3 source is
**not** included in this repository; the bullets below are kept for
historical context only.

- **v3.x (2025)** — alignment actions context menu, global keyboard
  shortcuts configuration UI, `tmx2source` and `vcs_manager`, OmegaT
  segmentation config compatibility, 3-column alignment dialog with
  navigation shortcuts, auto / enforce / mt translation memory
  managers.
- **v3.0** — initial public release of the desktop CAT-style tool.

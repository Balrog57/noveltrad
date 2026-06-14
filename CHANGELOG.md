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
- Corpus evaluation runner (`python -m tests.corpus.evaluate`) that
  emits deterministic offline JSON metrics for structure and
  terminology checks.
- Project privacy action: Recent Projects can clear local caches and
  stored metadata through `DELETE /projects/{project_id}/local-data`.
- Shared literary prompt contracts for LLM-backed agents.
- CI test matrix now covers Windows and Linux for Python 3.11/3.12
  while keeping the release workflow Windows-only.

### Changed
- Release documentation now treats `latest.json` `download_url` as the
  updater source of truth and documents best-effort Authenticode
  verification.

## [4.1.3] — 2026-06-14

### Fixed
- French UI translation now loads from the saved language setting and
  ships with the compiled Qt `.qm` catalogue in frozen builds.
- The installer can be displayed in English or French and records the
  initial application language without overwriting an existing user
  config.
- The Translate workflow exposes a visible return-to-file-selection
  action from Pipeline and Review pages.
- The release workflow verifies the generated
  `Setup_NovelTrad-v<version>.exe` before uploading release assets.
- Reviewer reflection metadata is persisted correctly.

### Tests
- Added focused reflection-loop, DAG escalation, and guarded headless
  client smoke coverage.

## [4.0.1] — 2026-06-11

### Added
- **Multi-file batch translation** (`FileCloud` widget): the Translate
  tab now accepts one *or many* files via drag-and-drop or the
  multi-select file dialog, dedupes them, and shows each as a badge
  with the right extension icon. The pipeline tags every chunk with
  the `source_file` column (new in `state_store.chunks`) and the
  Assembler now writes **one output file per source**, suffixed with
  the source's stem (e.g. `out_alpha.txt`, `out_beta.txt`).
- **Lexicon hard delete**: `DELETE /lexicon/{term_id}` is now a real
  `DELETE` in the state store. The GUI asks for confirmation before
  removing one or more terms; the glossary table refreshes
  immediately.
- **i18n infrastructure** (`src/gui/i18n/`): the desktop client is
  translatable via Qt Linguist. The first shipped translation is
  French (`src/gui/i18n/noveltrad_fr.ts`). The Settings tab exposes a
  Language combobox; the chosen language is persisted in
  `ConfigManager` under `ui.language`. The runtime falls back to
  English when the compiled `.qm` is missing (e.g. on developer
  machines that haven't run `pylrelease6`).

### Tests
- `tests/test_lexicon_delete.py` (3 tests): hard delete removes
  the row, 404 on missing id, recreate-after-delete yields a new id.
- `tests/test_batch_translate.py` (7 tests): `FileCloud` emits a
  list on add, dedupes repeated paths, uses
  `QFileDialog.getOpenFileNames` for browse; `state_store` filters
  chunks by `source_file`; the assembler groups chunks by source
  and writes one output per group.
- `tests/test_i18n_smoke.py` (6 tests): the i18n helpers
  (`default_language`, `available_languages`, `has_translation`,
  `load_translator`) never raise and report the expected types.
  `ConfigManager` defaults `ui.language` to `en`.

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
  stacked layout (Translate, Projects, Glossaries, Files,
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

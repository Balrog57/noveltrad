# AGENTS.md

Guidance for AI coding agents working in this repository. Keep it short, repo-specific, and verified.

## What this is

NovelTrad Desktop — a PyQt6 desktop CAT (computer-assisted translation) app for novels and web novels.
Formats: EPUB, DOCX, TXT. Engines: Argos, NLLB (ctranslate2), OpenAI-compatible LLM, Google (deep-translator).
TM system is OmegaT-compliant (TMX 1.4b, `tm/enforce|auto|mt|penalty-XX|tmx2source`).

Repo is on Windows; the CI runner is `windows-latest` with Python 3.11.

## Entry points and layout

- App entrypoint: `src/main_qt.py` (NOT `src/main.py`). Run with `python src/main_qt.py`.
- Package layout: `src/{core,engines,formats,gui,utils}/`. GUI uses controllers in `src/gui/controllers/` (project, ai, tm, editor, tools).
- Project format: a `.ntrad` directory containing a `.noveltrad/` subdir (OmegaT-style layout: `source/`, `target/`, `tm/`, `glossary/`, `dictionary/`, `.repositories/`).
- Sample/example projects live in `projects/*.ntrad`. Do not commit new ones — they are ignored.

## Commands

- Install dev deps: `pip install -r requirements.txt`
- Run from source: `python src/main_qt.py`
- Standalone build: `python build_script.py` (runs `pyinstaller build.spec`). README mentions `.\Build-NovelTrad-Qt.bat` — that file does NOT exist; use `build_script.py`.
- Installer: compile `NovelTrad.iss` with Inno Setup 6 ISCC.exe (see README).
- "Compile check" (what CI actually runs): `python -m compileall src`

## Things agents frequently get wrong here

- **Import order is load-bearing.** `src/main_qt.py` imports `onnxruntime` and `ctranslate2` BEFORE `PyQt6` to avoid DLL conflicts (msvcp140, zlib). Preserve this order in any new entrypoint or test harness that touches Qt.
- **`argostranslate` is optional.** It transitively pulls Pydantic v1 / confection / thinc / spacy, which break type inference on Python 3.14. Always import inside `try/except` and gate features on `ARGOS_AVAILABLE` — do not import it at module top level.
- **First-run flow.** On first run, `ConfigManager.is_first_run()` triggers `FirstRunWizard`; exiting the wizard exits the app. Do not add blocking dialogs before this check.
- **Window focus on Windows.** When launched from a terminal the window can start behind it. `main_qt.py` already calls `raise_()` + `activateWindow()`; mirror this in any new entrypoint.
- **Performance bug already fixed in `LanguageManager`.** `get_supported_languages()` used to call `argos.get_installed_languages()` inside a loop over hundreds of language codes. The fix is to call it once before the loop. Do not reintroduce this.
- **Peewee model extensions.** `DictionaryManager.has_language(...)` exists as a `@staticmethod` returning `bool` (uses `.exists()` on `GlobalDictionaryTerm`). Use it instead of counting rows.
- **Menu → controller wiring.** After the controllers refactor, every action wired in `MainWindow.create_menu_bar` must point at `self.controller.method`. If a menu action silently does nothing, the handler is missing in the controller — not in `mainwindow.py`.
- **UI redundancy rule.** Actions already represented by an obvious icon in the header (Undo, Redo, Save) should NOT also be in text menus.
- **PyQt naming.** Use `statusBar()` (method) — do not name an instance attribute `status_bar`.

## Constraints from existing files

- `.agents/rules/rules.md` (French, `trigger: always_on`) is the only other agent instruction file. It requires updating `tasks/todo.md` (plan) and `tasks/lessons.md` (memory) — BUT both `tasks/` and `.agents/` are in `.gitignore`, so they are local-only. The public repo does not see them. Still update them locally for the dev who runs the same agent setup.
- `OmegaT_Doc/` is a local OmegaT reference (gitignored). Never publish or commit its contents.

## CI and validation

- Only validation in CI: `python -m compileall src` on `windows-latest`, Python 3.11. No tests, no linter, no formatter are wired up.
- There is no `tests/` directory in the repo (despite being referenced in `tasks/todo.md` as planned). Do not assume `pytest` will work.
- `pyproject.toml` pins `requires-python = ">=3.10"`. `__pycache__` shows code has been run on 3.12 and 3.14.

## TM and project conventions (OmegaT-style)

- TM folders under a project: `tm/enforce/` (100% exact, force-overwrite), `tm/auto/` (100% exact, auto-insert, no overwrite), `tm/mt/` (red highlight, no overwrite), `tm/mt/penalty-NN/` (fuzzy score minus NN%), `tm/tmx2source/LL-PP.tmx` (third-language reference, exact match only).
- TMX export uses TMX 1.4b with `x-noveltrad:*` custom props (`status`, `engine`, `timestamp`, `chapter`, `schema_version`).
- Backup manager: snapshot every ~3 min, max 10 rotated, with `pre_modification` label support.

## Manual smoke-test before declaring done

This project has no automated test suite. After non-trivial changes, at minimum:
1. `python -m compileall src` (what CI runs).
2. `python src/main_qt.py` launches without traceback; first-run wizard appears if `config.json` is absent; subsequent runs open directly.
3. Open or create a `.ntrad` project under `projects/` and confirm the main window renders.

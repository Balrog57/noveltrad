# NovelTrad

NovelTrad is a PyQt6 desktop app for translating long-form fiction with a
FastAPI backend and a multi-agent pipeline. The v4 workflow accepts a text-like
document, chunks it, runs specialized agents for fast translation, lexicon
building, glossary application, consistency checks, QA, grammar proofing, LLM
polishing, and final assembly.

## Architecture

```text
PyQt6 desktop client
  - Translate / Settings / Glossaries / Files tabs
  - Activity log over WebSocket
  - HITL popup and chunk detail dialog

FastAPI backend
  - SQLite StateStore
  - multiprocessing worker manager
  - 9 agent stages
  - Ollama/OpenAI-compatible LLM router
```

The backend can run independently from the UI. The UI starts it automatically
when launched from `src/main_qt.py`, or it can be run directly for API testing.

## Repository Layout

```text
src/
  main_qt.py                  # Desktop entrypoint
  backend/
    server.py                 # FastAPI app and CLI
    orchestrator/             # State store, pipeline, worker lifecycle
    agents/                   # Parser, translator, QA, polisher, assembler
    engines/                  # NLLB wrapper
    formats/                  # EPUB/DOCX/TXT/SRT readers and chunker
    llm_router/               # Ollama + OpenAI-compatible routing/cache
  gui/
    app_config.py             # v4 JSON config
    main_window.py            # Minimal 4-tab shell
    backend_client.py         # HTTP/WebSocket client
    tabs/
    widgets/
    dialogs/
```

## Install

```powershell
pip install -r requirements.txt
```

Optional local model setup:

```powershell
ollama pull gemma3:4b
```

## Run

```powershell
python src/main_qt.py
```

Backend only:

```powershell
python -m src.backend.server --host 127.0.0.1 --port 8765
```

## Build

```powershell
python build_script.py
```

The build uses `build.spec` and writes `dist/NovelTrad/NovelTrad.exe`.
Compile `NovelTrad.iss` with Inno Setup 6 to create a Windows installer.

## Validation

```powershell
python -m compileall src
python -m src.backend.server --db-path .smoke.db
python src/main_qt.py
```

Manual smoke test:

1. Launch the desktop app.
2. Drop a small EPUB, DOCX, TXT, or SRT file.
3. Start a translation batch.
4. Confirm the activity log receives backend events.
5. Open the Files tab and inspect chunk details.

## Notes

- The active architecture is v4 only. Previous CAT/TM modules have been
  removed from the source tree.
- `config.json`, local projects, smoke-test SQLite files, virtual
  environments, and agent-local planning folders are ignored.
- Ollama is serialized by default to avoid overloading local hardware.

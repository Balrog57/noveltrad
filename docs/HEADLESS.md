# NovelTrad v4 — Headless / API mode

The backend can run as a standalone FastAPI server without the GUI. This
is useful for automation, CI, batch translation, or building custom
front-ends.

## Start the backend

```bash
python -m src.backend.server --host 127.0.0.1 --port 8765
```

CLI options:

- `--host`, `--port` — bind address.
- `--db`, `--db-path` — SQLite state DB path (default: `./.noveltrad_state.db`).
- `--vectors` — LanceDB vector directory (default: `./.noveltrad_vectors`).

## Health check

```bash
curl http://127.0.0.1:8765/health
```

Returns version, NLLB diagnostics, LLM provider mode, and usage counters.

## Core API flow

### 1. Create a project and trigger parsing

```bash
curl -X POST http://127.0.0.1:8765/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "project_dir": "./project_demo",
    "source_path": "./book.txt",
    "source_lang": "en",
    "target_lang": "fr",
    "output_path": "./book_fr.txt",
    "output_format": "txt",
    "profile": "balanced",
    "parse": true
  }'
```

`profile` can be `eco`, `balanced`, or `premium`.
`output_format` can be `txt`, `epub`, `epub_bilingual`, `docx`, `srt`.

### 2. Poll pipeline state

```bash
curl http://127.0.0.1:8765/pipeline/state
```

Wait until `output_artifact.output_path` is set.

### 3. Replay failed / hash-mismatched chunks

```bash
curl -X POST http://127.0.0.1:8765/pipeline/replay-chunks \
  -H "Content-Type: application/json" \
  -d '{"chunk_ids": ["chunk-id-1", "chunk-id-2"]}'
```

### 4. Manually assemble output

If the pipeline did not auto-assemble, trigger it:

```bash
curl -X POST http://127.0.0.1:8765/assemble \
  -H "Content-Type: application/json" \
  -d '{"output_path": "./book_fr.txt", "format": "txt"}'
```

## WebSocket activity stream

Connect to `ws://127.0.0.1:8765/ws` to receive live events:

- `pipeline_started`
- `agent_done`
- `chunk_hash_mismatch`
- `reflection_triggered`
- `reflection_exhausted`
- `hltl_alert`
- `chunks_replayed`
- `pipeline_shutdown`

## Example Python client

See [`examples/headless_client.py`](../examples/headless_client.py) for a
complete, dependency-light reference implementation.

## Environment variables

- `NOVELTRAD_HOST` / `NOVELTRAD_PORT` — default bind values.
- `NOVELTRAD_DB` — default SQLite state DB path.
- `NOVELTRAD_VECTORS` — default LanceDB directory.
- `NOVELTRAD_FAKE_LLM=1` — use offline fake LLM responses (tests only).
- `NOVELTRAD_TRANSLATION_TEST_MODE=1` — use fake local translator (tests only).

## Authentication

No authentication is implemented in v4. Run behind a reverse proxy or on
`127.0.0.1` for single-user, local-first usage.

#!/usr/bin/env python3
"""
NovelTrad CLI — contrôle total du backend en ligne de commande.

Usage:
    python -m src.backend.cli translate <file> [options]
    python -m src.backend.cli project list|create|delete|inspect|clean
    python -m src.backend.cli pipeline status|stop|pause|resume|replay
    python -m src.backend.cli glossary list|add|remove|search
    python -m src.backend.cli config show|set|path
    python -m src.backend.cli chunk list|show|replay
    python -m src.backend.cli hltl list|respond
    python -m src.backend.cli batch <dir> [options]
    python -m src.backend.cli server [--port 8765]
    python -m src.backend.cli health

Mode embedded (défaut): TestClient FastAPI, pas de serveur séparé.
Mode remote: avec --remote, se connecte à un backend déjà lancé.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ── Embedded app factory + config loader ──────────────────────────────

def _load_config(verbose: bool = False) -> None:
    """Apply user config to env vars (NLLB_MODEL, OLLAMA_MODEL, etc.)."""
    try:
        from src.gui.app_config import ConfigManager
        ConfigManager().apply_environment()
        if verbose:
            print(f"[cli] Config loaded: NLLB={os.environ.get('NLLB_MODEL','?')}, LLM={os.environ.get('OLLAMA_MODEL','?')}")
    except Exception as e:
        if verbose:
            print(f"[cli] Config skipped: {e}")


def _make_client():
    """Return a FastAPI TestClient with config loaded."""
    from fastapi.testclient import TestClient
    from src.backend.server import create_app
    tmp = tempfile.mkdtemp(prefix="noveltrad_cli_")
    app = create_app(db_path=Path(tmp) / ".state.db", vector_dir=Path(tmp) / ".vectors")
    return TestClient(app)


# ── Remote helpers ────────────────────────────────────────────────────

def _base_url() -> str:
    return f"http://{os.environ.get('NOVELTRAD_HOST','127.0.0.1')}:{os.environ.get('NOVELTRAD_PORT','8765')}"

def _api_get(path: str):
    import requests
    r = requests.get(f"{_base_url()}{path}", timeout=10)
    r.raise_for_status()
    return r.json()

def _api_post(path: str, data: dict | None = None):
    import requests
    r = requests.post(f"{_base_url()}{path}", json=data or {}, timeout=30)
    r.raise_for_status()
    return r.json()

def _api_delete(path: str):
    import requests
    r = requests.delete(f"{_base_url()}{path}", timeout=10)
    r.raise_for_status()
    return r.json()


# ═══════════════════════════════════════════════════════════════════════
# TRANSLATE
# ═══════════════════════════════════════════════════════════════════════

def cmd_translate(args) -> int:
    source = Path(args.source)
    if not source.exists():
        print(f"ERROR: file not found: {source}")
        return 1

    if args.test_mode:
        os.environ["NOVELTRAD_TRANSLATION_TEST_MODE"] = "1"
    if args.fake_llm:
        os.environ["NOVELTRAD_FAKE_LLM"] = "1"

    _load_config(verbose=args.verbose)

    output_dir = args.output or (source.parent / "output")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "project_dir": str(source.parent),
        "source_path": str(source),
        "source_lang": args.source_lang,
        "target_lang": args.target_lang,
        "output_path": str(output_dir / f"{source.stem}_{args.target_lang}.txt"),
        "output_format": args.format,
        "parse": True,
        "profile": args.profile,
    }

    client = _make_client()
    print(f"[translate] {source.name}  {args.source_lang}→{args.target_lang}  profile={args.profile}")

    res = client.post("/projects", json=payload)
    if res.status_code != 200:
        print(f"ERROR: {res.status_code} {res.text}")
        return 1

    pid = res.json()["project_id"]
    print(f"[translate] project={pid}  status=running")

    start = time.time()
    dots = 0
    while time.time() - start < args.timeout:
        state = client.get("/pipeline/state").json()
        art = state.get("output_artifact") or {}
        if art.get("output_path"):
            elapsed = time.time() - start
            out = Path(art["output_path"])
            text = out.read_text(encoding="utf-8") if out.exists() else ""
            print(f"\n[translate] ✓ DONE  {elapsed:.1f}s  {len(text)} chars  {len(text.splitlines())} lines")
            print(f"[translate] output: {out}")
            if not args.quiet:
                preview = text.splitlines()[:20]
                for line in preview:
                    print(f"  {line}")
                if len(text.splitlines()) > 20:
                    print(f"  ... ({len(text.splitlines()) - 20} more lines)")
            return 0
        proj = state.get("project") or {}
        if proj.get("status") in ("error", "stopped"):
            print(f"\n[translate] ✗ {proj['status']}")
            for e in state.get("event_log_tail", []):
                if e.get("level") == "error":
                    print(f"  {e.get('message','')}")
            return 1
        time.sleep(0.5)
        dots += 1
        if dots % 4 == 0:
            print(".", end="", flush=True)
    print(f"\n[translate] ✗ TIMEOUT after {args.timeout}s")
    return 1


# ═══════════════════════════════════════════════════════════════════════
# PROJECT
# ═══════════════════════════════════════════════════════════════════════

def cmd_project(args) -> int:
    client = _make_client()

    if args.action == "list":
        data = client.get("/projects").json()
        projects = data.get("projects", [])
        if not projects:
            print("[project] No projects found.")
            return 0
        print(f"{'ID':<14} {'Status':<10} {'Source':<40} {'Lang'}")
        print("-" * 75)
        for p in projects:
            sid = p.get("project_id", "")[:12]
            src = Path(p.get("source_path", "")).name or p.get("source_paths", ["?"])[0]
            lang = f"{p.get('source_lang','?')}→{p.get('target_lang','?')}"
            print(f"{sid:<14} {p.get('status','?'):<10} {src:<40} {lang}")
        return 0

    if args.action == "inspect":
        pid = args.project_id
        state = client.get("/pipeline/state").json()
        proj = state.get("project") or {}
        if proj.get("project_id") == pid:
            print(json.dumps(proj, indent=2, default=str))
            # Also show chunks
            workers = state.get("workers", {})
            if workers:
                print(f"\nWorkers: {list(workers.keys())}")
            return 0
        # Try project list
        projects = client.get("/projects").json().get("projects", [])
        for p in projects:
            if p.get("project_id") == pid:
                print(json.dumps(p, indent=2, default=str))
                return 0
        print(f"Project {pid} not found")
        return 1

    if args.action == "delete":
        pid = args.project_id
        try:
            client.delete(f"/projects/{pid}/local-data")
            print(f"[project] Deleted {pid}")
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
        return 0

    if args.action == "clean":
        pid = args.project_id
        try:
            client.delete(f"/projects/{pid}/local-data")
            print(f"[project] Cleaned {pid}")
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
        return 0

    return 0


# ═══════════════════════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def cmd_pipeline(args) -> int:
    client = _make_client()

    if args.action == "status":
        state = client.get("/pipeline/state").json()
        proj = state.get("project")
        if proj is None:
            print("[pipeline] No active project.")
            queue = state.get("project_queue", [])
            if queue:
                print(f"[pipeline] Queued: {len(queue)}")
                for q in queue:
                    print(f"  {q.get('project_id','?')}: {q.get('source_path','?')}")
            return 0
        print(f"Project:  {proj.get('project_id','?')}")
        print(f"Status:   {proj.get('status','?')}")
        print(f"Lang:     {proj.get('source_lang','?')}→{proj.get('target_lang','?')}")
        print(f"Profile:  {proj.get('profile','?')}")
        workers = state.get("workers", {})
        if workers:
            print(f"Workers ({len(workers)}):")
            for k, v in workers.items():
                bar = "✓" if v.get("stage_completed") else ("●" if v.get("active") else "○")
                print(f"  {bar} {k}")
        hltl = state.get("pending_hltl", 0)
        if hltl:
            print(f"⚠ Pending HITL: {hltl}")
        art = state.get("output_artifact") or {}
        if art.get("output_path"):
            print(f"Output:   {art['output_path']}")
        return 0

    if args.action == "stop":
        client.post("/pipeline/stop")
        print("[pipeline] Stop requested")
        return 0

    if args.action == "pause":
        client.post("/pipeline/pause")
        print("[pipeline] Pause requested")
        return 0

    if args.action == "resume":
        client.post("/pipeline/resume")
        print("[pipeline] Resume requested")
        return 0

    if args.action == "replay":
        client.post("/pipeline/replay-chunks", json={"chunk_ids": args.chunk_ids})
        print(f"[pipeline] Replaying {len(args.chunk_ids)} chunks")
        return 0

    return 0


# ═══════════════════════════════════════════════════════════════════════
# GLOSSARY
# ═══════════════════════════════════════════════════════════════════════

def cmd_glossary(args) -> int:
    client = _make_client()

    if args.action == "list":
        data = client.get("/lexicon/terms").json()
        terms = data.get("terms", [])
        if not terms:
            print("[glossary] Empty.")
            return 0
        print(f"{'Source':<25} {'Target':<25} {'Category':<15}")
        print("-" * 70)
        for t in terms[:50]:
            print(f"{t.get('source',''):<25} {t.get('target',''):<25} {t.get('category',''):<15}")
        if len(terms) > 50:
            print(f"  ... ({len(terms) - 50} more)")
        return 0

    if args.action == "add":
        payload = {
            "source": args.source_term,
            "target": args.target_term,
            "category": args.category or "",
            "confidence": 1.0,
            "validated_by_user": True,
        }
        client.post("/lexicon/terms", json=payload)
        print(f"[glossary] Added: {args.source_term} → {args.target_term}")
        return 0

    if args.action == "remove":
        # Search for term
        data = client.get("/lexicon/terms").json()
        terms = data.get("terms", [])
        found = [t for t in terms if t.get("source") == args.source_term]
        if not found:
            print(f"[glossary] Term not found: {args.source_term}")
            return 1
        for t in found:
            tid = t.get("id") or t.get("term_id")
            if tid:
                client.delete(f"/lexicon/terms/{tid}")
                print(f"[glossary] Removed: {args.source_term}")
        return 0

    if args.action == "search":
        data = client.get("/lexicon/terms").json()
        terms = data.get("terms", [])
        q = args.query.lower()
        matches = [t for t in terms if q in t.get("source", "").lower() or q in t.get("target", "").lower()]
        if not matches:
            print(f"[glossary] No matches for '{args.query}'")
            return 0
        print(f"[glossary] {len(matches)} matches for '{args.query}':")
        for t in matches:
            print(f"  {t.get('source','')} → {t.get('target','')}  [{t.get('category','')}]")
        return 0

    return 0


# ═══════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════

def cmd_config(args) -> int:
    from src.gui.app_config import ConfigManager
    mgr = ConfigManager()

    if args.action == "show":
        print(json.dumps(mgr.config, indent=2, default=str))
        return 0

    if args.action == "path":
        print(mgr.config_path)
        return 0

    if args.action == "set":
        keys = args.key.split(".")
        value = args.value
        # Try to parse as JSON for nested values
        try:
            value = json.loads(args.value)
        except (json.JSONDecodeError, ValueError):
            pass
        # Navigate to the right nested key
        cfg = mgr.config
        for k in keys[:-1]:
            if k not in cfg:
                cfg[k] = {}
            cfg = cfg[k]
        cfg[keys[-1]] = value
        mgr.save()
        print(f"[config] Set {args.key} = {json.dumps(value)}")
        if args.key.startswith("llm.") or args.key.startswith("nllb."):
            print("[config] ⚠ Restart the backend for changes to take effect.")
        return 0

    return 0


# ═══════════════════════════════════════════════════════════════════════
# CHUNK
# ═══════════════════════════════════════════════════════════════════════

def cmd_chunk(args) -> int:
    client = _make_client()

    if args.action == "list":
        state = client.get("/pipeline/state").json()
        store = state.get("state_store", {})
        # Chunks are in the state store under various keys
        # Look for chunk entries
        chunks = []
        for k, v in store.items():
            if "chunk" in k.lower() and isinstance(v, dict):
                chunks.append(v)
        if not chunks:
            print("[chunk] No chunks in active pipeline state.")
            print("[chunk] Try running a translation first, then check status.")
            return 0
        print(f"[chunk] {len(chunks)} chunks found:")
        for c in chunks[:20]:
            cid = str(c.get("chunk_id", c.get("id", "?")))[:16]
            status = c.get("status", "?")
            text_preview = str(c.get("source_text", c.get("raw_translation", "")))[:60]
            print(f"  {cid}  [{status}]  {text_preview}")
        return 0

    if args.action == "show":
        state = client.get("/pipeline/state").json()
        store = state.get("state_store", {})
        for k, v in store.items():
            if isinstance(v, dict) and v.get("chunk_id") == args.chunk_id:
                print(json.dumps(v, indent=2, default=str))
                return 0
        print(f"[chunk] Chunk {args.chunk_id} not found in current state.")
        return 1

    if args.action == "replay":
        client.post("/pipeline/replay-chunks", json={"chunk_ids": [args.chunk_id]})
        print(f"[chunk] Replaying {args.chunk_id}")
        return 0

    return 0


# ═══════════════════════════════════════════════════════════════════════
# HITL (Human-in-the-Loop)
# ═══════════════════════════════════════════════════════════════════════

def cmd_hltl(args) -> int:
    client = _make_client()

    if args.action == "list":
        state = client.get("/pipeline/state").json()
        pending = state.get("pending_hltl", 0)
        if not pending:
            print("[hltl] No pending HITL requests.")
            return 0
        print(f"[hltl] {pending} pending requests")
        # Get details from event log
        for e in state.get("event_log_tail", []):
            if e.get("type") == "hitl_request":
                print(f"  ID: {e.get('request_id','?')}")
                print(f"  Chunk: {e.get('chunk_id','?')}")
                print(f"  Question: {e.get('question','?')}")
                print()
        return 0

    if args.action == "respond":
        payload = {"request_id": args.request_id, "answer": args.answer}
        try:
            client.post("/hltl/respond", json=payload)
            print(f"[hltl] Response sent for {args.request_id}")
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
        return 0

    return 0


# ═══════════════════════════════════════════════════════════════════════
# BATCH
# ═══════════════════════════════════════════════════════════════════════

def cmd_batch(args) -> int:
    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"ERROR: not a directory: {directory}")
        return 1

    # Find all translatable files
    exts = {".txt", ".epub", ".docx", ".srt"}
    files = sorted(
        [f for f in directory.iterdir() if f.suffix.lower() in exts and f.is_file()],
        key=lambda f: f.name,
    )

    if not files:
        print(f"[batch] No translatable files found in {directory}")
        return 0

    # Filter
    if args.filter:
        import fnmatch
        files = [f for f in files if fnmatch.fnmatch(f.name.lower(), args.filter.lower())]

    if args.limit:
        files = files[: args.limit]

    print(f"[batch] {len(files)} files to translate")
    if args.dry_run:
        for f in files:
            print(f"  {f.name}")
        return 0

    if args.test_mode:
        os.environ["NOVELTRAD_TRANSLATION_TEST_MODE"] = "1"
    if args.fake_llm:
        os.environ["NOVELTRAD_FAKE_LLM"] = "1"

    _load_config(verbose=args.verbose)

    output_dir = Path(args.output or (directory / "output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    fail = 0
    total_start = time.time()

    client = _make_client()
    print(f"[batch] Backend ready, starting {len(files)} files...")

    for f in files:
        print(f"\n{'─'*60}")
        print(f"[batch] {f.name}  ({ok+fail+1}/{len(files)})")

        payload = {
            "project_dir": str(directory),
            "source_path": str(f),
            "source_lang": args.source_lang,
            "target_lang": args.target_lang,
            "output_path": str(output_dir / f"{f.stem}_{args.target_lang}.txt"),
            "output_format": args.format,
            "parse": True,
            "profile": args.profile,
        }

        try:
            res = client.post("/projects", json=payload)
            if res.status_code != 200:
                print(f"  ERROR creating project: {res.text}")
                fail += 1
                continue
        except Exception as e:
            print(f"  ERROR: {e}")
            fail += 1
            continue

        pid = res.json()["project_id"]
        start = time.time()

        while time.time() - start < args.timeout:
            state = client.get("/pipeline/state").json()
            art = state.get("output_artifact") or {}
            if art.get("output_path"):
                elapsed = time.time() - start
                out = Path(art["output_path"])
                size = out.stat().st_size if out.exists() else 0
                print(f"  ✓ {elapsed:.1f}s  {size} bytes  → {out.name}")
                ok += 1
                break
            proj = state.get("project") or {}
            if proj.get("status") in ("error", "stopped"):
                print(f"  ✗ {proj['status']}")
                fail += 1
                break
            time.sleep(0.5)
        else:
            print(f"  ✗ TIMEOUT")
            fail += 1

    total_elapsed = time.time() - total_start
    print(f"\n{'═'*60}")
    print(f"[batch] DONE  {ok} ok  {fail} failed  {total_elapsed:.0f}s total")
    return 0 if fail == 0 else 1


# ═══════════════════════════════════════════════════════════════════════
# SERVER
# ═══════════════════════════════════════════════════════════════════════

def cmd_server(args) -> int:
    _load_config(verbose=True)
    from src.backend.server import main as server_main
    print(f"[server] Starting on http://127.0.0.1:{args.port}")
    server_main(["--host", "127.0.0.1", "--port", str(args.port)])
    return 0


# ═══════════════════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════════════════

def cmd_health(args) -> int:
    _load_config(verbose=False)
    client = _make_client()
    data = client.get("/health").json()
    print(json.dumps(data, indent=2, default=str))
    return 0


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="noveltrad", description="NovelTrad CLI")
    sub = parser.add_subparsers(dest="command")

    # ── translate ──
    t = sub.add_parser("translate", help="Translate a file")
    t.add_argument("source", type=Path, help="Source file")
    t.add_argument("--target-lang", default="fr")
    t.add_argument("--source-lang", default="en")
    t.add_argument("--profile", default="balanced", choices=["eco", "balanced", "premium"])
    t.add_argument("--format", default="txt", choices=["txt", "epub", "docx", "srt"])
    t.add_argument("--output", type=Path, help="Output directory")
    t.add_argument("--test-mode", action="store_true")
    t.add_argument("--fake-llm", action="store_true")
    t.add_argument("--timeout", type=float, default=600.0)
    t.add_argument("--verbose", "-v", action="store_true")
    t.add_argument("--quiet", "-q", action="store_true")

    # ── project ──
    p = sub.add_parser("project", help="Project management")
    pa = p.add_subparsers(dest="action", required=True)
    pa.add_parser("list", help="List all projects")
    pi = pa.add_parser("inspect", help="Show project details")
    pi.add_argument("project_id")
    pd = pa.add_parser("delete", help="Delete a project")
    pd.add_argument("project_id")
    pc = pa.add_parser("clean", help="Clean project data files")
    pc.add_argument("project_id")

    # ── pipeline ──
    pl = sub.add_parser("pipeline", help="Pipeline control")
    pla = pl.add_subparsers(dest="action", required=True)
    pla.add_parser("status", help="Show pipeline state")
    pla.add_parser("stop", help="Stop pipeline")
    pla.add_parser("pause", help="Pause pipeline")
    pla.add_parser("resume", help="Resume pipeline")
    pr = pla.add_parser("replay", help="Replay chunks")
    pr.add_argument("chunk_ids", nargs="+")

    # ── glossary ──
    g = sub.add_parser("glossary", help="Glossary management")
    ga = g.add_subparsers(dest="action", required=True)
    ga.add_parser("list", help="List all terms")
    gadd = ga.add_parser("add", help="Add a term")
    gadd.add_argument("source_term")
    gadd.add_argument("target_term")
    gadd.add_argument("--category")
    grem = ga.add_parser("remove", help="Remove a term")
    grem.add_argument("source_term")
    gs = ga.add_parser("search", help="Search glossary")
    gs.add_argument("query")

    # ── config ──
    c = sub.add_parser("config", help="Configuration")
    ca = c.add_subparsers(dest="action", required=True)
    ca.add_parser("show", help="Show full config")
    ca.add_parser("path", help="Show config file path")
    cs = ca.add_parser("set", help="Set a config value")
    cs.add_argument("key")
    cs.add_argument("value")

    # ── chunk ──
    ch = sub.add_parser("chunk", help="Chunk operations")
    cha = ch.add_subparsers(dest="action", required=True)
    cha.add_parser("list", help="List chunks in active project")
    chs = cha.add_parser("show", help="Show chunk details")
    chs.add_argument("chunk_id")
    chr_ = cha.add_parser("replay", help="Replay a chunk")
    chr_.add_argument("chunk_id")

    # ── hltl ──
    h = sub.add_parser("hltl", help="Human-in-the-Loop")
    ha = h.add_subparsers(dest="action", required=True)
    ha.add_parser("list", help="List pending HITL requests")
    hr = ha.add_parser("respond", help="Respond to a HITL request")
    hr.add_argument("request_id")
    hr.add_argument("answer")

    # ── batch ──
    b = sub.add_parser("batch", help="Batch translate a directory")
    b.add_argument("directory", type=Path)
    b.add_argument("--target-lang", default="fr")
    b.add_argument("--source-lang", default="en")
    b.add_argument("--profile", default="eco")
    b.add_argument("--format", default="txt")
    b.add_argument("--output", type=Path)
    b.add_argument("--filter", help="Glob filter (e.g. '00*.txt')")
    b.add_argument("--limit", type=int, help="Max files to process")
    b.add_argument("--test-mode", action="store_true")
    b.add_argument("--fake-llm", action="store_true")
    b.add_argument("--timeout", type=float, default=300.0)
    b.add_argument("--verbose", "-v", action="store_true")
    b.add_argument("--dry-run", action="store_true", help="List files without translating")

    # ── server ──
    s = sub.add_parser("server", help="Start backend server")
    s.add_argument("--port", type=int, default=8765)

    # ── health ──
    sub.add_parser("health", help="Health check + diagnostics")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    # Ensure requests is available (used by some subcommands via _api_*)
    try:
        import requests  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])

    handlers = {
        "translate": cmd_translate,
        "project": cmd_project,
        "pipeline": cmd_pipeline,
        "glossary": cmd_glossary,
        "config": cmd_config,
        "chunk": cmd_chunk,
        "hltl": cmd_hltl,
        "batch": cmd_batch,
        "server": cmd_server,
        "health": cmd_health,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

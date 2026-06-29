"""``batch`` subcommand: translate every translatable file in a directory.

The flow is the same as ``translate`` (POST /projects, poll /pipeline/state)
but loops over a glob-filtered file list. Dry-run mode just lists the
files. Non-dry-run mode drives the full pipeline per file and tallies
success / failure counts.
"""
from __future__ import annotations

import os
import time
from argparse import ArgumentParser
from pathlib import Path

from ..cli_client import get_client, load_config


def add_arguments(sub: ArgumentParser) -> None:
    sub.add_argument("directory", type=Path)
    sub.add_argument("--target-lang", default="fr")
    sub.add_argument("--source-lang", default="en")
    sub.add_argument("--profile", default="eco")
    sub.add_argument("--format", default="txt")
    sub.add_argument("--output", type=Path)
    sub.add_argument("--filter", help="Glob filter (e.g. '00*.txt')")
    sub.add_argument("--limit", type=int, help="Max files to process")
    sub.add_argument("--test-mode", action="store_true")
    sub.add_argument("--fake-llm", action="store_true")
    sub.add_argument("--timeout", type=float, default=300.0)
    sub.add_argument("--verbose", "-v", action="store_true")
    sub.add_argument("--dry-run", action="store_true", help="List files without translating")


def run(args) -> int:
    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"ERROR: not a directory: {directory}")
        return 1

    exts = {".txt", ".epub", ".docx", ".srt"}
    files = sorted(
        [f for f in directory.iterdir() if f.suffix.lower() in exts and f.is_file()],
        key=lambda f: f.name,
    )

    if not files:
        print(f"[batch] No translatable files found in {directory}")
        return 0

    if args.filter:
        import fnmatch

        files = [
            f for f in files if fnmatch.fnmatch(f.name.lower(), args.filter.lower())
        ]

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

    load_config(verbose=args.verbose)

    output_dir = Path(args.output or (directory / "output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    fail = 0
    total_start = time.time()

    client = get_client(args)
    print(f"[batch] Backend ready, starting {len(files)} files...")

    for f in files:
        print(f"\n{'='*60}")
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
                print(f"  OK {elapsed:.1f}s  {size} bytes  -> {out.name}")
                ok += 1
                break
            proj = state.get("project") or {}
            if proj.get("status") in ("error", "stopped"):
                print(f"  FAIL {proj['status']}")
                fail += 1
                break
            time.sleep(0.5)
        else:
            print(f"  FAIL TIMEOUT")
            fail += 1

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"[batch] DONE  {ok} ok, {fail} failed  ({total_elapsed:.0f}s)")
    return 0 if fail == 0 else 1

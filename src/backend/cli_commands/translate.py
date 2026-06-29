"""``translate`` subcommand: translate a single file via the API.

Implements the argparse wiring for ``noveltrad translate <file>`` and the
``cmd_translate`` body that drives the translation, polls the pipeline
state, and prints the result.

Behavior unchanged from the v3.5 monolithic cli.py: the same flags, the
same status polling loop, the same output preview. The only structural
change is that this module no longer contains the argparse tree for the
other nine subcommands.
"""
from __future__ import annotations

import os
import time
from argparse import ArgumentParser
from pathlib import Path

from ..cli_client import get_client, load_config


def add_arguments(sub: ArgumentParser) -> None:
    sub.add_argument("source", type=Path, help="Source file")
    sub.add_argument("--target-lang", default="fr")
    sub.add_argument("--source-lang", default="en")
    sub.add_argument(
        "--profile",
        default="balanced",
        choices=["eco", "balanced", "premium"],
    )
    sub.add_argument(
        "--format",
        default="txt",
        choices=["txt", "epub", "docx", "srt"],
    )
    sub.add_argument("--output", type=Path, help="Output directory")
    sub.add_argument("--test-mode", action="store_true")
    sub.add_argument("--fake-llm", action="store_true")
    sub.add_argument("--timeout", type=float, default=600.0)
    sub.add_argument("--verbose", "-v", action="store_true")
    sub.add_argument("--quiet", "-q", action="store_true")


def run(args) -> int:
    source = Path(args.source)
    if not source.exists():
        print(f"ERROR: file not found: {source}")
        return 1

    if args.test_mode:
        os.environ["NOVELTRAD_TRANSLATION_TEST_MODE"] = "1"
    if args.fake_llm:
        os.environ["NOVELTRAD_FAKE_LLM"] = "1"

    load_config(verbose=args.verbose)

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

    client = get_client(args)
    print(
        f"[translate] {source.name}  {args.source_lang}->{args.target_lang}  "
        f"profile={args.profile}"
    )

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
            print(
                f"\n[translate] OK DONE  {elapsed:.1f}s  {len(text)} chars  "
                f"{len(text.splitlines())} lines"
            )
            print(f"[translate] output: {out}")
            if not args.quiet:
                preview = text.splitlines()[:20]
                for line in preview:
                    print(f"  {line}")
                if len(text.splitlines()) > 20:
                    print(
                        f"  ... ({len(text.splitlines()) - 20} more lines)"
                    )
            return 0
        proj = state.get("project") or {}
        if proj.get("status") in ("error", "stopped"):
            print(f"\n[translate] FAIL {proj['status']}")
            for e in state.get("event_log_tail", []):
                if e.get("level") == "error":
                    print(f"  {e.get('message','')}")
            return 1
        time.sleep(0.5)
        dots += 1
        if dots % 4 == 0:
            print(".", end="", flush=True)
    print(f"\n[translate] FAIL TIMEOUT after {args.timeout}s")
    return 1

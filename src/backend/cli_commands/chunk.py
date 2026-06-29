"""``chunk`` subcommand: list / show / replay chunks in the active project."""
from __future__ import annotations

import json
from argparse import ArgumentParser

from ..cli_client import get_client


def add_arguments(sub: ArgumentParser) -> None:
    pa = sub.add_subparsers(dest="action", required=True)
    pa.add_parser("list", help="List chunks in active project")
    chs = pa.add_parser("show", help="Show chunk details")
    chs.add_argument("chunk_id")
    chr_ = pa.add_parser("replay", help="Replay a chunk")
    chr_.add_argument("chunk_id")


def run(args) -> int:
    client = get_client(args)

    if args.action == "list":
        state = client.get("/pipeline/state").json()
        store = state.get("state_store", {})
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
            text_preview = str(
                c.get("source_text", c.get("raw_translation", ""))
            )[:60]
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

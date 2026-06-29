"""``hltl`` subcommand: list / respond to pending human-in-the-loop requests."""
from __future__ import annotations

from argparse import ArgumentParser

from ..cli_client import get_client


def add_arguments(sub: ArgumentParser) -> None:
    pa = sub.add_subparsers(dest="action", required=True)
    pa.add_parser("list", help="List pending HITL requests")
    hr = pa.add_parser("respond", help="Respond to a HITL request")
    hr.add_argument("request_id")
    hr.add_argument("answer")


def run(args) -> int:
    client = get_client(args)

    if args.action == "list":
        state = client.get("/pipeline/state").json()
        pending = state.get("pending_hltl", 0)
        if not pending:
            print("[hltl] No pending HITL requests.")
            return 0
        print(f"[hltl] {pending} pending requests")
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

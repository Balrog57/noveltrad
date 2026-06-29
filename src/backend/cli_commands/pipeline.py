"""``pipeline`` subcommand: status / stop / pause / resume / replay."""
from __future__ import annotations

from argparse import ArgumentParser

from ..cli_client import get_client


def add_arguments(sub: ArgumentParser) -> None:
    pa = sub.add_subparsers(dest="action", required=True)
    pa.add_parser("status", help="Show pipeline state")
    pa.add_parser("stop", help="Stop pipeline")
    pa.add_parser("pause", help="Pause pipeline")
    pa.add_parser("resume", help="Resume pipeline")
    pr = pa.add_parser("replay", help="Replay chunks")
    pr.add_argument("chunk_ids", nargs="+")


def run(args) -> int:
    client = get_client(args)

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
        print(f"Lang:     {proj.get('source_lang','?')}->{proj.get('target_lang','?')}")
        print(f"Profile:  {proj.get('profile','?')}")
        workers = state.get("workers", {})
        if workers:
            print(f"Workers ({len(workers)}):")
            for k, v in workers.items():
                bar = "OK" if v.get("stage_completed") else ("*" if v.get("active") else "-")
                print(f"  {bar} {k}")
        hltl = state.get("pending_hltl", 0)
        if hltl:
            print(f"WARNING Pending HITL: {hltl}")
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

"""``server`` subcommand: start the backend server."""
from __future__ import annotations

from argparse import ArgumentParser

from ..cli_client import load_config


def add_arguments(sub: ArgumentParser) -> None:
    sub.add_argument("--port", type=int, default=8765)


def run(args) -> int:
    load_config(verbose=True)
    from src.backend.server import main as server_main

    print(f"[server] Starting on http://127.0.0.1:{args.port}")
    server_main(["--host", "127.0.0.1", "--port", str(args.port)])
    return 0

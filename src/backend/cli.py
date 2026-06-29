#!/usr/bin/env python3
"""
NovelTrad CLI — contrôle total du backend en ligne de commande.

Usage:
    python -m src.backend.cli translate <file> [options]
    python -m src.backend.cli project list|create|delete|inspect|clean|activate|rename|active
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
import subprocess
import sys

from . import cli_commands
from .cli_client import load_config  # re-exported for back-compat


# Each entry: (command name, module). The module exposes
# ``add_arguments(sub)`` and ``run(args) -> int``.
_COMMANDS: list[tuple[str, object]] = [
    ("translate", cli_commands.translate),
    ("project", cli_commands.project),
    ("pipeline", cli_commands.pipeline),
    ("glossary", cli_commands.glossary),
    ("config", cli_commands.config),
    ("chunk", cli_commands.chunk),
    ("hltl", cli_commands.hltl),
    ("batch", cli_commands.batch),
    ("server", cli_commands.server),
    ("health", cli_commands.health),
]


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argparse tree by delegating to each command."""
    parser = argparse.ArgumentParser(prog="noveltrad", description="NovelTrad CLI")
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Connect to a running backend (default: embedded TestClient)",
    )
    sub = parser.add_subparsers(dest="command")
    for name, module in _COMMANDS:
        module.add_arguments(sub.add_parser(name, help=_help_for(name)))
    return parser


def _help_for(name: str) -> str:
    """Short description for ``--help`` output of each subcommand."""
    return {
        "translate": "Translate a single file",
        "project": "Project management",
        "pipeline": "Pipeline control",
        "glossary": "Glossary management",
        "config": "Configuration",
        "chunk": "Chunk operations",
        "hltl": "Human-in-the-Loop requests",
        "batch": "Batch translate a directory",
        "server": "Start the backend server",
        "health": "Health check + diagnostics",
    }.get(name, "")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    # Ensure requests is available (used by some subcommands via the
    # remote client). Done once at startup so the first subcommand
    # call does not stall on a pip install.
    try:
        import requests  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])

    # Dispatch to the matching module's ``run`` function.
    for name, module in _COMMANDS:
        if name == args.command:
            return module.run(args)
    # Unreachable: argparse rejected unknown commands before we got here.
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

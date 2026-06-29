"""CLI subcommands.

Each module exports two callables:

  * ``add_arguments(sub)`` -- registers the subparser and its args.
  * ``run(args) -> int``    -- executes the subcommand; returns exit code.

The dispatcher in ``src/backend/cli.py`` builds the argparse tree by
calling each module's ``add_arguments`` and then dispatches the parsed
``args`` to the matching ``run``.

Adding a new subcommand
-----------------------
1. Drop a new ``yourcmd.py`` here exporting ``add_arguments`` + ``run``.
2. Register it in ``src/backend/cli.py`` (one line in ``_COMMANDS``).
"""
from . import batch, chunk, config, glossary, hltl, health, pipeline, project, server, translate

__all__ = [
    "batch",
    "chunk",
    "config",
    "glossary",
    "hltl",
    "health",
    "pipeline",
    "project",
    "server",
    "translate",
]

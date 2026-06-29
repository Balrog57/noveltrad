"""``health`` subcommand: dump the /health endpoint response."""
from __future__ import annotations

import json
from argparse import ArgumentParser

from ..cli_client import get_client, load_config


def add_arguments(sub: ArgumentParser) -> None:
    # No sub-args: ``noveltrad health`` is a single call.
    pass


def run(args) -> int:
    load_config(verbose=False)
    client = get_client(args)
    data = client.get("/health").json()
    print(json.dumps(data, indent=2, default=str))
    return 0

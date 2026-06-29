"""``config`` subcommand: show / path / set user config values.

Reads and writes the user config (the same one ConfigManager drives
from the GUI). Set accepts dot-notation keys (``llm.provider``) and
JSON-typed values when possible.
"""
from __future__ import annotations

import json
from argparse import ArgumentParser

from src.gui.app_config import ConfigManager


def add_arguments(sub: ArgumentParser) -> None:
    pa = sub.add_subparsers(dest="action", required=True)
    pa.add_parser("show", help="Show full config")
    pa.add_parser("path", help="Show config file path")
    cs = ca = pa.add_parser("set", help="Set a config value")  # noqa: F841
    cs.add_argument("key")
    cs.add_argument("value")


def run(args) -> int:
    mgr = ConfigManager()

    if args.action == "show":
        print(json.dumps(mgr.config, indent=2, default=str))
        return 0

    if args.action == "path":
        print(mgr.CONFIG_FILE)
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
        mgr.save_config()
        print(f"[config] Set {args.key} = {json.dumps(value)}")
        if args.key.startswith("llm.") or args.key.startswith("nllb."):
            print("[config] WARNING Restart the backend for changes to take effect.")
        return 0

    return 0

"""Backward-compatible shim — delegates to ``build.py --all``.

Kept so older CI scripts and developer muscle memory continue to work.
New code should call ``python build.py`` directly.
"""

import sys

from build import main


if __name__ == "__main__":
    sys.exit(main(["--all"]))

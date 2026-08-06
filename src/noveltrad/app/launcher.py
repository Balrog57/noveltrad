"""PID 1 launcher (SDD 6.2).

Starts app/worker.py then Streamlit with app/main.py, relays SIGTERM and
waits for their shutdown. Refuses to start a second Worker: the presence
of the single process is guaranteed by the single container.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def main() -> None:
    """Launch the Worker, then Streamlit; supervise until both exit."""
    worker = subprocess.Popen(
        [sys.executable, "-m", "noveltrad.app.worker"],
        cwd=_repo_root(),
    )
    streamlit = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(_repo_root() / "src" / "noveltrad" / "app" / "main.py"),
            "--server.address=0.0.0.0",
            "--server.port=8501",
            "--server.headless=true",
            "--server.maxUploadSize=512",
            "--server.maxMessageSize=512",
            "--server.enableXsrfProtection=true",
            "--server.enableCORS=true",
            "--browser.gatherUsageStats=false",
        ],
        cwd=_repo_root(),
    )

    stop_requested = False

    def relay(_signum, _frame) -> None:  # noqa: ANN001
        nonlocal stop_requested
        stop_requested = True
        worker.terminate()
        streamlit.terminate()

    if os.name != "nt":
        signal.signal(signal.SIGTERM, relay)
        signal.signal(signal.SIGINT, relay)

    try:
        while worker.poll() is None and streamlit.poll() is None:
            time.sleep(1)
        if stop_requested:
            worker.terminate()
            streamlit.terminate()
        worker.wait()
        streamlit.wait()
    except KeyboardInterrupt:
        relay(None, None)
        worker.wait()
        streamlit.wait()


def _repo_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[3]


if __name__ == "__main__":
    main()

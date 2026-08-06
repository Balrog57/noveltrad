"""Worker process entry (SDD 20.12 app/worker.py).

Runs the single logical FIFO loop with heartbeat and cooperative shutdown.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import sys

from noveltrad.app.container import Container
from noveltrad.core.logging import LogContext, new_correlation_id


async def _run() -> None:
    container = Container()
    worker = container.build_worker()
    container.system_repo.heartbeat("Starting")

    stop_event = asyncio.Event()

    def request_stop() -> None:
        worker.request_stop()
        stop_event.set()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            with contextlib.suppress(NotImplementedError, RuntimeError):
                loop.add_signal_handler(sig, request_stop)

    container.logs.record(
        "INFO",
        "app.start",
        "worker started",
        LogContext(correlation_id=new_correlation_id()),
    )
    worker_task = asyncio.create_task(worker.run())
    try:
        await stop_event.wait()
    finally:
        container.logs.record(
            "INFO",
            "worker.stop",
            "worker stopping",
            LogContext(correlation_id=new_correlation_id()),
        )
        container.system_repo.heartbeat("StoppingAfterCall")
        await worker_task
        container.system_repo.heartbeat("Stopped")
        container.close()


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run())


if __name__ == "__main__":
    main()

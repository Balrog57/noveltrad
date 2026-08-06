"""Worker loop (SDD 12.14, 12.16).

Single logical loop consuming the persisted FIFO sequentially. The one-second
SQLite poll is the only wake-up mechanism; no Redis, local socket,
additional Worker thread or queue service is added.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from noveltrad.core.clock import utc_now
from noveltrad.core.logging import LogContext, LogService, new_correlation_id


@dataclass(slots=True)
class WorkerRuntime:
    """Shared worker runtime health state (SDD 8.8.5)."""

    state: str = "Starting"
    heartbeat_at: str = ""
    started_at: str = ""


class WorkerLoop:
    def __init__(
        self,
        job_service,
        translation_service,
        logs: LogService,
        poll_seconds: float = 1.0,
        heartbeat_seconds: float = 5.0,
        system_repo=None,
    ) -> None:
        self._job_service = job_service
        self._translation_service = translation_service
        self._logs = logs
        self._poll = poll_seconds
        self._heartbeat = heartbeat_seconds
        self._system_repo = system_repo
        self._stop_requested = False
        self._runtime = WorkerRuntime(started_at=utc_now().isoformat())
        self._last_persist = 0.0

    @property
    def runtime(self) -> WorkerRuntime:
        return self._runtime

    def request_stop(self) -> None:
        self._stop_requested = True

    async def run(self) -> None:
        """Recover interrupted jobs, then consume the FIFO until stopped."""
        self._runtime.state = "Starting"
        self._heartbeat()
        try:
            self._job_service.recover_interrupted()
            self._runtime.state = "Idle"
            while not self._stop_requested:
                job = self._job_service.take_next()
                if job is None:
                    self._runtime.state = "Idle"
                    self._heartbeat()
                    await asyncio.sleep(self._poll)
                    continue
                self._runtime.state = "Busy"
                try:
                    result = await self._translation_service.execute(job.id)
                    if result.completed:
                        self._job_service.mark_completed(job.id)
                    elif self._stop_requested:
                        self._runtime.state = "StoppingAfterCall"
                        self._job_service.apply_pause(job.id)
                    else:
                        await asyncio.sleep(self._poll)
                except Exception as exc:  # noqa: BLE001 - worker must not die
                    safe = str(exc)[:512]
                    self._job_service.mark_failed(job.id, "WORKER_ERROR")
                    self._logs.record(
                        "ERROR",
                        "system.error",
                        f"worker pipeline failure: {safe}",
                        LogContext(
                            correlation_id=new_correlation_id(),
                            job_id=job.id,
                        ),
                        error_code="WORKER_ERROR",
                    )
        finally:
            self._runtime.state = "StoppingAfterCall" if self._stop_requested else "Stopped"
            self._heartbeat()

    def _heartbeat(self) -> None:
        self._runtime.heartbeat_at = utc_now().isoformat()
        import time as _time

        now = _time.monotonic()
        if self._system_repo is not None and now - self._last_persist >= self._heartbeat:
            self._system_repo.heartbeat(self._runtime.state)
            self._last_persist = now

"""Base worker loop shared by all v4 agents.

Why a base class
----------------
The 9 agents in the v4 plan are heterogeneous (parsers, ML inference,
LLM calls, deterministic rules), but they all share the same outer
loop:

    while True:
        msg = input_queue.get()
        if msg is SENTINEL: break
        if msg["type"] == "control": handle(msg)
        else: handle_task(msg)
        output_queue.put({...})

By centralising that loop here we get:
  * uniform logging + error reporting
  * a single place to enforce the "agent is read-only on the State Store"
    rule — base_worker NEVER imports state_store; the worker asks the
    orchestrator for chunk data via control messages, or gets the data
    pre-fetched and stuffed into the task message.
  * a single place to handle pause / resume / shutdown sentinels.

Subclassing contract
--------------------
A concrete agent (e.g. `ParserAgent`) MUST override `handle_task(msg)`
and may override `setup()`, `teardown()`, and `handle_control(msg)`.

Message protocol
----------------
Task messages (light, JSON-serializable):
    {
        "msg_id":       "<uuid>",
        "type":         "task",
        "chunk_id":     "<uuid>" | None,
        "action":       "translate" | "qa_check" | "polish" | ...,
        "payload":      {...optional agent-specific data...},
        "correlation_id": "<uuid>" | None,
        "timestamp":    "<iso8601>",
    }

Control messages (orchestrator -> worker):
    {
        "msg_id":  "<uuid>",
        "type":    "control",
        "command": "pause" | "resume" | "shutdown" | "reconfigure",
        "args":    {...optional...},
    }

Response / progress messages (worker -> orchestrator) are written to
the worker's `output_queue` and have shape:
    {
        "msg_id":       "<uuid>",
        "type":         "progress" | "done" | "error" | "hltl_request",
        "chunk_id":     "<uuid>" | None,
        "stage":        "<stage_key>",
        "worker_id":    "<stage_key>__<pid>",
        "payload":      {...},
        "correlation_id": "<uuid>" | None,
    }

Threading model
---------------
Agents run as multiprocessing.Process on Windows (spawn). One process
per agent. The base worker uses no threads internally; concurrency
across chunks is achieved by spawning N worker processes for stages
declared parallelizable in `pipeline.PARALLELIZABLE_STAGES`.

Why not asyncio
---------------
The plan explicitly chose multiprocessing queues over asyncio for the
agent layer (§9, "FastAPI + subprocess" risk row). Heavy native
extensions (ctranslate2, onnxruntime) prefer release of the GIL and
predictable process isolation over coroutine scheduling.
"""

from __future__ import annotations

import logging
import os
import queue as _queue
import signal
import threading
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


# Sentinels carried over the control channel.
SHUTDOWN_SENTINEL: dict[str, Any] = {
    "msg_id": "sentinel",
    "type": "control",
    "command": "shutdown",
}
PAUSE_SENTINEL: dict[str, Any] = {
    "msg_id": "sentinel",
    "type": "control",
    "command": "pause",
}
RESUME_SENTINEL: dict[str, Any] = {
    "msg_id": "sentinel",
    "type": "control",
    "command": "resume",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_msg_id() -> str:
    return uuid.uuid4().hex


@dataclass
class WorkerIdentity:
    """How this worker identifies itself in messages and logs."""

    stage: str
    worker_id: str
    pid: int


class BaseWorker:
    """Standard event-loop for an agent subprocess.

    Subclasses implement `handle_task`. They MUST NOT import
    `state_store` — the orchestrator is the single writer.
    """

    #: If True, the agent will spawn a side thread to watch the control
    #: channel concurrently with task processing. Used by agents that
    #: may block on a long task (LLM call, NLLB inference).
    use_control_thread: bool = True

    def __init__(
        self,
        stage: str,
        input_queue: "_queue.Queue[dict[str, Any] | None]",
        output_queue: "_queue.Queue[dict[str, Any]]",
        control_queue: "_queue.Queue[dict[str, Any] | None]",
        worker_id: str | None = None,
        options: dict[str, Any] | None = None,
    ):
        self.stage = stage
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.control_queue = control_queue
        self.worker_id = worker_id or f"{stage}__{os.getpid()}"
        self.options = dict(options or {})
        self.identity = WorkerIdentity(
            stage=stage, worker_id=self.worker_id, pid=os.getpid()
        )
        self._paused = threading.Event()
        self._paused.set()  # initially NOT paused
        self._shutdown = threading.Event()
        self._control_thread: threading.Thread | None = None

    # ----- lifecycle hooks -----

    def setup(self) -> None:
        """Called once when the worker enters its run loop."""

    def teardown(self) -> None:
        """Called once just before the worker exits."""

    def handle_task(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        """Process one task message; return the result (None to skip emit).

        Returning a dict emits it on the output queue. Returning None
        suppresses emission (useful for already-handled control flows).
        """
        raise NotImplementedError

    def handle_control(self, msg: dict[str, Any]) -> None:
        """Process a control message. Default handles pause/resume/shutdown."""
        command = msg.get("command")
        if command == "pause":
            self._paused.clear()
            logger.info("[%s] paused", self.worker_id)
        elif command == "resume":
            self._paused.set()
            logger.info("[%s] resumed", self.worker_id)
        elif command == "shutdown":
            self._shutdown.set()
            # Also unblock the input queue so we exit promptly.
            self._paused.set()
        elif command == "reconfigure":
            self.options.update(msg.get("args") or {})
            logger.info("[%s] reconfigured: %s", self.worker_id, self.options)
        else:
            logger.warning("[%s] unknown control command: %r", self.worker_id, command)

    # ----- public entry point -----

    def run(self) -> None:
        """Main event loop. Returns when shutdown is requested."""
        # SIGINT should propagate so the orchestrator can clean up. We
        # don't install a custom handler — multiprocessing default is fine.
        try:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
        except (ValueError, OSError):
            # Not in main thread (Windows); ignore.
            pass

        logger.info("[%s] starting (pid=%d)", self.worker_id, os.getpid())
        try:
            self.setup()
        except Exception:
            logger.exception("[%s] setup() crashed", self.worker_id)
            self._emit_error(None, "setup_failed", traceback.format_exc())
            return

        if self.use_control_thread:
            self._control_thread = threading.Thread(
                target=self._control_loop,
                name=f"{self.worker_id}-ctrl",
                daemon=True,
            )
            self._control_thread.start()

        try:
            self._task_loop()
        finally:
            try:
                self.teardown()
            except Exception:
                logger.exception("[%s] teardown() crashed", self.worker_id)
            logger.info("[%s] exited", self.worker_id)

    # ----- internals -----

    def _task_loop(self) -> None:
        while not self._shutdown.is_set():
            self._paused.wait()
            if self._shutdown.is_set():
                break
            try:
                msg = self.input_queue.get(timeout=0.5)
            except _queue.Empty:
                continue
            if msg is None:
                # Treat None as a polite shutdown.
                self._shutdown.set()
                break
            try:
                result = self.handle_task(msg)
            except Exception as exc:
                tb = traceback.format_exc()
                logger.exception("[%s] handle_task crashed", self.worker_id)
                self._emit_error(
                    msg.get("chunk_id"), "task_exception", f"{exc}\n{tb}"
                )
                continue
            if result is not None:
                try:
                    self.output_queue.put(result, timeout=2.0)
                except _queue.Full:
                    logger.error(
                        "[%s] output queue full; dropping message %s",
                        self.worker_id,
                        result.get("msg_id"),
                    )

    def _control_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                msg = self.control_queue.get(timeout=0.5)
            except _queue.Empty:
                continue
            if msg is None:
                self._shutdown.set()
                break
            try:
                self.handle_control(msg)
            except Exception:
                logger.exception(
                    "[%s] handle_control crashed on %r", self.worker_id, msg
                )

    # ----- emit helpers -----

    def _emit_progress(
        self,
        chunk_id: str | None,
        percent: float,
        note: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"percent": float(percent), "note": note}
        if extra:
            payload.update(extra)
        self._emit("progress", chunk_id, payload)

    def _emit_error(
        self,
        chunk_id: str | None,
        kind: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"error_kind": kind, "message": message}
        if extra:
            payload.update(extra)
        self._emit("error", chunk_id, payload)

    def _emit_done(
        self,
        chunk_id: str | None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._emit("done", chunk_id, payload or {})

    def _emit_hltl(
        self,
        chunk_id: str,
        issue: dict[str, Any],
    ) -> None:
        self._emit("hltl_request", chunk_id, {"issue": issue})

    def _emit(
        self,
        msg_type: str,
        chunk_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        msg = {
            "msg_id": _new_msg_id(),
            "type": msg_type,
            "chunk_id": chunk_id,
            "stage": self.stage,
            "worker_id": self.worker_id,
            "timestamp": _now_iso(),
            "payload": payload,
        }
        try:
            self.output_queue.put(msg, timeout=2.0)
        except _queue.Full:
            logger.error(
                "[%s] output queue full while emitting %s", self.worker_id, msg_type
            )


# ---------- utilities for subclasses ----------


def now_ms() -> int:
    return int(time.time() * 1000)


def make_task_message(
    chunk_id: str,
    action: str,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build a task message. Used by tests and the orchestrator."""
    return {
        "msg_id": _new_msg_id(),
        "type": "task",
        "chunk_id": chunk_id,
        "action": action,
        "payload": dict(payload or {}),
        "correlation_id": correlation_id,
        "timestamp": _now_iso(),
    }


def make_control_message(command: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a control message. Used by the orchestrator."""
    return {
        "msg_id": _new_msg_id(),
        "type": "control",
        "command": command,
        "args": dict(args or {}),
        "timestamp": _now_iso(),
    }


__all__ = [
    "BaseWorker",
    "WorkerIdentity",
    "make_task_message",
    "make_control_message",
    "SHUTDOWN_SENTINEL",
    "PAUSE_SENTINEL",
    "RESUME_SENTINEL",
]

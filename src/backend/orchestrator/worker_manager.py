"""Worker lifecycle manager — spawn, monitor, restart, shutdown.

Each agent runs as a `multiprocessing.Process` (Windows-friendly via
spawn). The manager owns:

  * per-stage input/output queues (multiprocessing.Queue)
  * a per-stage control queue (so the orchestrator can pause/resume
    individual stages without killing them)
  * the Process objects themselves

The manager does NOT know about the State Store, the LLM router, or
HTTP. It exposes a thin lifecycle API used by the orchestrator:

    manager = WorkerManager(agent_registry, queue_registry)
    manager.start_stage("fast_translator", count=2)
    manager.pause_stage("fast_translator")
    manager.resume_stage("fast_translator")
    manager.shutdown()
    manager.is_alive("fast_translator") -> bool

`start_stage` is idempotent per (stage, instance) — calling it twice
won't spawn duplicates.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

from .pipeline import StageSpec, PARALLELIZABLE_STAGES

logger = logging.getLogger(__name__)


# Default parallel-worker counts when a stage is parallelizable.
# Realistic ceiling — Ollama & NLLB don't benefit from huge fan-out.
DEFAULT_PARALLELISM: dict[str, int] = {
    "fast_translator": 1,
    "llm_polisher": 1,
    "consistency_checker": 1,
}


@dataclass
class WorkerSlot:
    """One running worker process for a stage."""

    stage: str
    index: int
    process: mp.Process
    started_at: float = field(default_factory=time.time)
    restart_count: int = 0
    last_error: str | None = None


class StageQueues:
    """Bundle of queues used by one stage across all its worker instances."""

    def __init__(self, stage: str, input_channel: str, output_channel: str):
        self.stage = stage
        self.input_channel = input_channel
        self.output_channel = output_channel
        # All worker instances of a stage share the SAME input queue
        # (work is auto-distributed by Queue.get) and the SAME output
        # queue (orchestrator collects from one place). They each have
        # their own control queue — see below.
        self.input: mp.Queue = mp.Queue(maxsize=1024)
        self.output: mp.Queue = mp.Queue(maxsize=4096)
        # control queues are per-instance, owned by WorkerSlot
        self._controls: dict[int, mp.Queue] = {}
        self._lock = threading.Lock()

    def make_control_queue(self, key: int) -> mp.Queue:
        with self._lock:
            q = self._controls.get(key)
            if q is None:
                q = mp.Queue(maxsize=64)
                self._controls[key] = q
            return q

    def drop_control_queue(self, key: int) -> None:
        with self._lock:
            self._controls.pop(key, None)

    def close(self) -> None:
        for q in (self.input, self.output):
            try:
                q.close()
            except Exception:
                pass
        with self._lock:
            for q in self._controls.values():
                try:
                    q.close()
                except Exception:
                    pass
            self._controls.clear()


def _default_worker_entrypoint(
    stage: str,
    agent_module: str,
    worker_id: str,
    input_queue: mp.Queue,
    output_queue: mp.Queue,
    control_queue: mp.Queue,
    options: dict[str, Any],
) -> None:
    """Subprocess entrypoint.

    Imports the agent module, instantiates its `Worker` class, and
    calls `.run()`. Lives here (not in the agent modules) so the
    manager controls the exact import and constructor — agents stay
    small and dependency-free of multiprocessing wiring.
    """
    import importlib

    try:
        module = importlib.import_module(agent_module)
        worker_cls = getattr(module, "Worker", None)
        if worker_cls is None:
            raise RuntimeError(
                f"Agent module {agent_module!r} has no class 'Worker'"
            )
        # NOTE: queues are passed as the underlying multiprocessing.Queue
        # objects. The agent's __init__ signature must accept them.
        worker = worker_cls(
            stage=stage,
            input_queue=input_queue,
            output_queue=output_queue,
            control_queue=control_queue,
            worker_id=worker_id,
            options=options,
        )
        worker.run()
    except Exception:
        # The process is about to die anyway. Log the full traceback so it
        # shows up in the orchestrator's logs. We use ``logger`` rather
        # than ``print`` because in a frozen Windows build (``console=False``)
        # ``sys.stdout`` is ``None`` and a bare ``print`` would raise a
        # secondary ``AttributeError`` that masks the real crash.
        try:
            logger.exception("[%s] worker crashed", worker_id)
        except Exception:
            pass
        raise


class WorkerManager:
    """Owns all worker processes and their queues.

    Construct once per orchestrator lifetime. Call `start_stage` for
    every stage you want running, then `shutdown` to tear them all down.
    """

    def __init__(
        self,
        stages: dict[str, StageSpec],
        max_restarts: int = 3,
        restart_cooldown_s: float = 2.0,
    ):
        self._stages = dict(stages)
        self._queues: dict[str, StageQueues] = {}
        self._slots: dict[tuple[str, int], WorkerSlot] = {}
        self._lock = threading.RLock()
        self._max_restarts = max_restarts
        self._restart_cooldown_s = restart_cooldown_s
        self._shutdown_requested = False
        self._monitor_thread: threading.Thread | None = None
        self._on_worker_exit: Callable[[WorkerSlot, int], None] | None = None

    # ----- public surface -----

    def set_exit_hook(self, hook: Callable[[WorkerSlot, int], None]) -> None:
        """Register a callback invoked when a worker exits unexpectedly.

        The orchestrator uses this to decide whether to restart the
        stage or surface an error to the GUI.
        """
        self._on_worker_exit = hook

    def queues_for(self, stage: str) -> StageQueues:
        try:
            return self._queues[stage]
        except KeyError as exc:
            raise KeyError(f"Stage {stage!r} has no queues; was it started?") from exc

    def output_queue_for(self, stage: str) -> mp.Queue:
        return self.queues_for(stage).output

    def start_stage(self, stage: str, count: int | None = None) -> None:
        """Spawn `count` workers for the given stage (1 if not parallelizable)."""
        if self._shutdown_requested:
            raise RuntimeError("WorkerManager is shutting down")
        spec = self._stages.get(stage)
        if spec is None:
            raise KeyError(f"Unknown stage: {stage!r}")

        if count is None:
            count = DEFAULT_PARALLELISM.get(stage, 1)
        if spec.parallelizable:
            count = max(1, count)
        else:
            count = 1

        with self._lock:
            queues = self._queues.get(stage)
            if queues is None:
                queues = StageQueues(stage, spec.input_channel, spec.output_channel)
                self._queues[stage] = queues

            existing = [k for k in self._slots if k[0] == stage]
            if existing:
                # Idempotent: don't double-spawn.
                logger.info(
                    "start_stage(%s) called but stage already has %d workers",
                    stage,
                    len(existing),
                )
                return

            for index in range(count):
                self._spawn_one(spec, queues, index)

        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="worker-monitor",
                daemon=True,
            )
            self._monitor_thread.start()

    def _spawn_one(
        self, spec: StageSpec, queues: StageQueues, index: int
    ) -> WorkerSlot:
        worker_id = f"{spec.key}__{index}" if index > 0 else spec.key
        control_q = queues.make_control_queue(index)
        # NOTE: we share control_q across all workers spawned from the
        # orchestrator process. Each spawned worker will get a fresh
        # copy via inheritance of mp.Queue — they share state under
        # the hood, which is what we want (broadcast pause/resume).
        proc = mp.Process(
            target=_default_worker_entrypoint,
            name=f"agent-{spec.key}-{index}",
            args=(
                spec.key,
                spec.agent_module,
                worker_id,
                queues.input,
                queues.output,
                control_q,
                dict(spec.extra_options),
            ),
            daemon=True,
        )
        proc.start()
        slot = WorkerSlot(stage=spec.key, index=index, process=proc)
        self._slots[(spec.key, index)] = slot
        logger.info(
            "Started %s worker pid=%s (input=%s, output=%s)",
            spec.key,
            proc.pid,
            spec.input_channel,
            spec.output_channel,
        )
        return slot

    def _monitor_loop(self) -> None:
        """Watch worker PIDs and restart crashed ones (up to max_restarts)."""
        while not self._shutdown_requested:
            time.sleep(0.5)
            with self._lock:
                dead: list[tuple[WorkerSlot, int]] = []
                for key, slot in list(self._slots.items()):
                    if not slot.process.is_alive():
                        exit_code = slot.process.exitcode
                        dead.append((slot, exit_code))
                for slot, exit_code in dead:
                    self._handle_dead_worker(slot, exit_code)

    def _handle_dead_worker(self, slot: WorkerSlot, exit_code: int) -> None:
        # Remove the slot first so we don't re-handle it.
        self._slots.pop((slot.stage, slot.index), None)
        queues = self._queues.get(slot.stage)
        if queues is not None:
            queues.drop_control_queue(slot.index)

        if self._shutdown_requested:
            return

        if slot.restart_count >= self._max_restarts:
            logger.error(
                "Worker %s pid=%s exited (code=%s) and exceeded max restarts; giving up",
                slot.stage,
                slot.process.pid,
                exit_code,
            )
            if self._on_worker_exit is not None:
                try:
                    self._on_worker_exit(slot, exit_code)
                except Exception:
                    logger.exception("on_worker_exit hook raised")
            return

        time.sleep(self._restart_cooldown_s)

        spec = self._stages.get(slot.stage)
        if spec is None or queues is None:
            return

        # Re-acquire lock to respawn.
        with self._lock:
            # Double-check nobody else respawned it.
            if (slot.stage, slot.index) in self._slots:
                return
            new_slot = self._spawn_one(spec, queues, slot.index)
            new_slot.restart_count = slot.restart_count + 1
            new_slot.last_error = (
                f"previous exit code={exit_code} pid={slot.process.pid}"
            )

    # ----- pause / resume / shutdown -----

    def _broadcast_control(self, stage: str, msg: dict[str, Any]) -> None:
        queues = self._queues.get(stage)
        if queues is None:
            return
        for slot in list(self._slots.values()):
            if slot.stage != stage:
                continue
            ctrl = queues.make_control_queue(slot.index)
            try:
                ctrl.put(msg, timeout=1.0)
            except Exception:
                logger.warning(
                    "Failed to deliver control %s to %s",
                    msg.get("command"),
                    slot.worker_id,
                )

    def pause_stage(self, stage: str) -> None:
        from ..agents.base_worker import PAUSE_SENTINEL

        self._broadcast_control(stage, PAUSE_SENTINEL)

    def resume_stage(self, stage: str) -> None:
        from ..agents.base_worker import RESUME_SENTINEL

        self._broadcast_control(stage, RESUME_SENTINEL)

    def shutdown_stage(self, stage: str) -> None:
        from ..agents.base_worker import SHUTDOWN_SENTINEL

        self._broadcast_control(stage, SHUTDOWN_SENTINEL)

    def shutdown(self, timeout: float = 5.0) -> None:
        self._shutdown_requested = True
        for stage in list(self._queues.keys()):
            self.shutdown_stage(stage)
        deadline = time.time() + timeout
        for slot in list(self._slots.values()):
            remaining = max(0.0, deadline - time.time())
            slot.process.join(timeout=remaining)
            if slot.process.is_alive():
                logger.warning(
                    "Worker %s pid=%s did not exit; terminating",
                    slot.stage,
                    slot.process.pid,
                )
                slot.process.terminate()
                slot.process.join(timeout=1.0)
        for q in self._queues.values():
            q.close()
        self._slots.clear()
        self._queues.clear()

    # ----- diagnostics -----

    def is_alive(self, stage: str) -> bool:
        return any(
            slot.process.is_alive() for (s, _), slot in self._slots.items() if s == stage
        )

    def snapshot(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for (stage, index), slot in self._slots.items():
            entry = out.setdefault(
                stage,
                {"count": 0, "workers": []},
            )
            entry["count"] += 1
            entry["workers"].append(
                {
                    "index": index,
                    "pid": slot.process.pid,
                    "alive": slot.process.is_alive(),
                    "restart_count": slot.restart_count,
                    "last_error": slot.last_error,
                }
            )
        return out

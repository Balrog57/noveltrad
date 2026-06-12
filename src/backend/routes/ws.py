"""WebSocket event-stream endpoint."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .deps import Deps


def register(app: Any, deps: Deps) -> None:
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()

        def push(event: dict[str, Any]) -> None:
            try:
                loop = websocket.app.state._ws_loop  # type: ignore[attr-defined]
            except AttributeError:
                loop = None
            if loop is None or loop.is_closed():
                return
            asyncio.run_coroutine_threadsafe(
                _safe_send(websocket, event), loop
            )

        websocket.app.state._ws_loop = asyncio.get_event_loop()
        deps.orchestrator.add_listener(push)
        try:
            while True:
                # Drain incoming pings; the GUI uses this to stay
                # connected and we use it to detect disconnect.
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        finally:
            deps.orchestrator.remove_listener(push)


async def _safe_send(ws: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await ws.send_json(payload)
    except Exception:
        pass


__all__ = ["register"]

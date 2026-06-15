"""HTTP/WebSocket client for the NovelTrad v4 backend.

GUI-process code uses this client to talk to the FastAPI server
spawned by `main_qt.py`. The client is intentionally tiny — no
caching, no retries — the backend already retries LLM calls.

Threading: requests run on a background thread and emit Qt signals
back to the GUI. The WebSocket reader also runs on a side thread.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class BackendError(RuntimeError):
    pass


class BackendClient:
    """Minimal HTTP + WebSocket client for the v4 backend."""

    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        self.base_url = base_url.rstrip("/")
        self._ws: Any | None = None
        self._ws_thread: threading.Thread | None = None
        self._ws_callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._ws_lock = threading.Lock()
        self._stop = threading.Event()

    # ----- HTTP -----

    def get(
        self,
        path: str,
        timeout: float = 5.0,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self._request("GET", path, params=params, timeout=timeout)

    def post(self, path: str, body: dict[str, Any] | None = None, timeout: float = 30.0) -> Any:
        return self._request("POST", path, body=body, timeout=timeout)

    def put(self, path: str, body: dict[str, Any] | None = None, timeout: float = 10.0) -> Any:
        return self._request("PUT", path, body=body, timeout=timeout)

    def delete(self, path: str, timeout: float = 10.0) -> Any:
        return self._request("DELETE", path, timeout=timeout)

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> Any:
        if params:
            from urllib.parse import urlencode

            qs = urlencode(
                {k: v for k, v in params.items() if v is not None and v != ""},
                doseq=False,
            )
            if qs:
                path = f"{path}?{qs}" if "?" not in path else f"{path}&{qs}"
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", errors="replace")
                if not raw:
                    return None
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
        except urllib.error.HTTPError as exc:
            raise BackendError(f"{method} {path} -> HTTP {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise BackendError(f"{method} {path} -> {exc.reason}") from exc

    def health(self) -> dict[str, Any]:
        return self.get("/health", timeout=2.0) or {}

    def wait_ready(self, timeout_s: float = 15.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                if self.health().get("ok"):
                    return True
            except Exception:
                pass
            time.sleep(0.3)
        return False

    # ----- WebSocket -----

    def open_websocket(self, on_event: Callable[[dict[str, Any]], None]) -> bool:
        """Open the /ws connection in a background thread.

        Returns True if the thread was started (the WS may not be
        connected yet — callers should treat the events stream as
        the source of truth).
        """
        with self._ws_lock:
            self._ws_callbacks.append(on_event)
            if self._ws_thread is not None and self._ws_thread.is_alive():
                return True
            self._stop.clear()
            self._ws_thread = threading.Thread(
                target=self._ws_loop, name="backend-ws", daemon=True
            )
            self._ws_thread.start()
            return True

    def close(self) -> None:
        self._stop.set()
        with self._ws_lock:
            self._ws_callbacks.clear()

    def _ws_loop(self) -> None:
        import socket
        import base64
        import os
        import struct

        url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        path = "/ws"
        # Parse host:port
        try:
            _, rest = url.split("://", 1)
            host_port = rest.split("/", 1)[0]
            if ":" in host_port:
                host, port_s = host_port.split(":", 1)
                port = int(port_s)
            else:
                host = host_port
                port = 80
        except Exception as exc:
            logger.error("Bad backend URL %r: %s", self.base_url, exc)
            return

        backoff = 0.5
        while not self._stop.is_set():
            try:
                sock = socket.create_connection((host, port), timeout=5.0)
                key = base64.b64encode(os.urandom(16)).decode("ascii")
                handshake = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {host}:{port}\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Key: {key}\r\n"
                    "Sec-WebSocket-Version: 13\r\n\r\n"
                )
                sock.sendall(handshake.encode("ascii"))
                # Read response headers
                buf = b""
                while b"\r\n\r\n" not in buf:
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise RuntimeError("ws handshake closed")
                    buf += chunk
                if b" 101 " not in buf.split(b"\r\n", 1)[0]:
                    raise RuntimeError(f"ws handshake failed: {buf[:200]!r}")
                backoff = 0.5
                # Read frames
                while not self._stop.is_set():
                    header = self._recv_exact(sock, 2)
                    if not header:
                        raise RuntimeError("ws closed")
                    b1, b2 = header[0], header[1]
                    opcode = b1 & 0x0F
                    masked = (b2 & 0x80) != 0
                    length = b2 & 0x7F
                    if length == 126:
                        ext = self._recv_exact(sock, 2)
                        length = struct.unpack("!H", ext)[0]
                    elif length == 127:
                        ext = self._recv_exact(sock, 8)
                        length = struct.unpack("!Q", ext)[0]
                    mask = self._recv_exact(sock, 4) if masked else b""
                    payload = self._recv_exact(sock, length) if length else b""
                    if masked and mask:
                        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                    if opcode == 0x1:  # text
                        try:
                            msg = json.loads(payload.decode("utf-8", errors="replace"))
                        except Exception:
                            continue
                        with self._ws_lock:
                            cbs = list(self._ws_callbacks)
                        for cb in cbs:
                            try:
                                cb(msg)
                            except Exception:
                                logger.exception("ws callback raised")
                    elif opcode == 0x8:  # close
                        raise RuntimeError("ws close frame")
            except Exception as exc:
                logger.debug("ws loop: %s (reconnect in %.1fs)", exc, backoff)
                if self._stop.is_set():
                    return
                # Jittered exponential backoff (full jitter: 0..backoff)
                import random as _random
                sleep_for = _random.uniform(0, backoff)
                time.sleep(sleep_for)
                backoff = min(8.0, backoff * 2)

    @staticmethod
    def _recv_exact(sock: Any, n: int) -> bytes:
        out = b""
        while len(out) < n:
            chunk = sock.recv(n - len(out))
            if not chunk:
                return out
            out += chunk
        return out


__all__ = ["BackendClient", "BackendError"]

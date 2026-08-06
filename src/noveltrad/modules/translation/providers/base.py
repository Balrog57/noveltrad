"""AIProvider protocol and shared HTTP client (SDD 14.14).

One async httpx client without retry; timeouts connect=10/read=300/write=30/
pool=10; limits max_connections=2, max_keepalive_connections=1;
follow_redirects=False; trust_env=False; TLS verification always on.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from noveltrad.core.contracts import (
    CompletionRequest,
    CompletionResponse,
    PipelineSnapshot,
    ValidationReport,
)

_TIMEOUT = httpx.Timeout(connect=10, read=300, write=30, pool=10)
_LIMITS = httpx.Limits(max_connections=2, max_keepalive_connections=1)


def build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=_TIMEOUT,
        limits=_LIMITS,
        follow_redirects=False,
        trust_env=False,
    )


class AIProvider(Protocol):
    async def validate_configuration(self, snapshot: PipelineSnapshot) -> ValidationReport: ...
    async def list_models(self) -> tuple[str, ...]: ...
    async def complete(self, request: CompletionRequest) -> CompletionResponse: ...
    async def close(self) -> None: ...

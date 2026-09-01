"""Production HTTP middleware: request IDs, tracing, and rate limiting."""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from cfi_core.observability import new_request_id, trace_span

REQUEST_ID_HEADER = "X-Request-ID"
RATE_LIMIT_HEADER = "X-RateLimit-Limit"
RATE_REMAINING_HEADER = "X-RateLimit-Remaining"
BYPASS_PATHS = frozenset({"/health", "/ready", "/metrics", "/accountant"})


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request ID and best-effort trace span to every request."""

    def __init__(self, app: ASGIApp, service: str) -> None:
        super().__init__(app)
        self._service = service

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or new_request_id()
        request.state.request_id = request_id
        attributes = {
            "service.name": self._service,
            "http.route": request.url.path,
            "request.id": request_id,
        }
        with trace_span("http.request", attributes):
            response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-client rate limiter (fail-open on health probes)."""

    def __init__(self, app: ASGIApp, max_requests: int, window_seconds: int = 60) -> None:
        super().__init__(app)
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        if request.client is None:
            return "unknown"
        return request.client.host

    def _allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self._window_seconds:
            window.popleft()
        if len(window) >= self._max_requests:
            return False, 0
        window.append(now)
        return True, self._max_requests - len(window)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in BYPASS_PATHS:
            return await call_next(request)
        allowed, remaining = self._allow(self._client_key(request))
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate_limit_exceeded"},
                headers={
                    "Retry-After": str(self._window_seconds),
                    RATE_LIMIT_HEADER: str(self._max_requests),
                    RATE_REMAINING_HEADER: "0",
                },
            )
        response = await call_next(request)
        response.headers[RATE_LIMIT_HEADER] = str(self._max_requests)
        response.headers[RATE_REMAINING_HEADER] = str(remaining)
        return response


def rate_limit_from_env() -> int:
    """Return requests-per-minute limit; 0 disables rate limiting."""
    return int(os.getenv("CFI_RATE_LIMIT_RPM", "0"))


def configure_service_app(app: FastAPI, service: str) -> FastAPI:
    """Install production middleware on a FastAPI service."""
    app.add_middleware(RequestContextMiddleware, service=service)
    limit = rate_limit_from_env()
    if limit > 0:
        app.add_middleware(RateLimitMiddleware, max_requests=limit, window_seconds=60)
    return app

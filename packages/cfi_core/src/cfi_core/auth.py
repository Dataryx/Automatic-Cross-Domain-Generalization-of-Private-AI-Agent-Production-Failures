"""Optional bearer-token API authentication for service endpoints."""

from __future__ import annotations

import os
import secrets

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

AUTH_BYPASS_PATHS = frozenset({"/health", "/ready", "/metrics", "/accountant", "/review/ui", "/tracing"})


def api_token_from_env() -> str | None:
    token = os.getenv("CFI_API_TOKEN")
    if token:
        return token
    return None


def authorize_bearer(header_value: str | None, expected: str) -> bool:
    if not header_value or not header_value.startswith("Bearer "):
        return False
    provided = header_value.removeprefix("Bearer ").strip()
    return secrets.compare_digest(provided, expected)


def auth_required(path: str, method: str) -> bool:
    if path in AUTH_BYPASS_PATHS:
        return False
    if method == "GET" and path.endswith("/ui"):
        return False
    return True


class ApiTokenMiddleware(BaseHTTPMiddleware):
    """Require bearer token when CFI_API_TOKEN is configured (fail-closed on mutations)."""

    def __init__(self, app: ASGIApp, token: str | None) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._token or not auth_required(request.url.path, request.method):
            return await call_next(request)
        if not authorize_bearer(request.headers.get("Authorization"), self._token):
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})
        return await call_next(request)

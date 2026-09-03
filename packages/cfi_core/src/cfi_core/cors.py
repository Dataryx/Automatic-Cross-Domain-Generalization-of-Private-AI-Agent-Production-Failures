"""Optional CORS for dashboard and external clients."""

from __future__ import annotations

import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware


def cors_origins_from_env() -> list[str]:
    raw = os.getenv("CFI_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def configure_cors(app: FastAPI) -> FastAPI:
    """Allow configured browser origins (dashboard dev server by default)."""
    origins = cors_origins_from_env()
    if not origins:
        return app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

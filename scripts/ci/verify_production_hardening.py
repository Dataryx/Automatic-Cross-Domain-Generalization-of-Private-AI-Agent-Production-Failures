#!/usr/bin/env python3
"""Verify production hardening: request tracing headers and optional rate limits."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cfi_core.middleware import REQUEST_ID_HEADER
from cfi_registry import RegistryStore, create_app


def main() -> int:
    client = TestClient(create_app(RegistryStore()))
    resp = client.get("/health", headers={REQUEST_ID_HEADER: "hardening-smoke"})
    if resp.status_code != 200:
        print(f"health failed: {resp.status_code}", file=sys.stderr)
        return 1
    if resp.headers.get(REQUEST_ID_HEADER) != "hardening-smoke":
        print("request ID not echoed", file=sys.stderr)
        return 1

    app = FastAPI()

    @app.get("/work")
    def work() -> dict[str, str]:
        return {"ok": "true"}

    from cfi_core.middleware import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)
    limited = TestClient(app)
    if limited.get("/work").status_code != 200:
        return 1
    if limited.get("/work").status_code != 200:
        return 1
    if limited.get("/work").status_code != 429:
        print("rate limit did not trigger", file=sys.stderr)
        return 1

    print("Production hardening verification OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

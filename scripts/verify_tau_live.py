#!/usr/bin/env python3
"""Verify τ-bench live task fetch via in-process tau stub."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from fastapi.testclient import TestClient

from eval.benchmarks import tau_live
from eval.benchmarks.tau_adapter import evaluate_tasks
from services.tau_stub.main import app


class _StubResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


def main() -> int:
    client = TestClient(app)
    if client.get("/health").status_code != 200:
        print("tau_stub health failed", file=sys.stderr)
        return 1
    tasks = client.get("/v1/tasks").json()
    if not tasks:
        print("tau_stub tasks endpoint empty", file=sys.stderr)
        return 1

    os.environ["CFI_TAU_BENCH_URL"] = "http://stub/v1/tasks"
    original_get = httpx.get

    def patched_get(url: str, **kwargs: Any) -> _StubResponse:
        if url.rstrip("/").endswith("/v1/tasks"):
            return _StubResponse(tasks)
        return _StubResponse(original_get(url, **kwargs).json())

    tau_live.httpx.get = patched_get  # type: ignore[method-assign, assignment]
    try:
        results = evaluate_tasks()
    finally:
        tau_live.httpx.get = original_get  # type: ignore[method-assign, assignment]
        os.environ.pop("CFI_TAU_BENCH_URL", None)

    if not results or not all(r.compiled for r in results):
        print("τ-live adapter compile failed", file=sys.stderr)
        return 1
    if "Remote task fetch" not in " ".join(results[0].assumptions):
        print("τ-live assumptions missing", file=sys.stderr)
        return 1
    print(f"tau-live adapter OK: {len(results)} tasks")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Sandboxed τ-bench task stub (format adapter hook, not live τ-bench)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from cfi_core.middleware import configure_service_app
from cfi_core.observability import service_health

TASKS_PATH = Path(__file__).resolve().parents[2] / "eval" / "benchmarks" / "tau_tasks.json"
TASKS = json.loads(TASKS_PATH.read_text(encoding="utf-8"))

app = FastAPI(title="CFI τ-bench Task Stub")
configure_service_app(app, "tau_stub")


@app.get("/health")
def health() -> dict[str, str]:
    return service_health("tau_stub")


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"ready": "true", "service": "tau_stub"}


@app.get("/v1/tasks")
def list_tasks() -> list[dict]:
    return TASKS


if __name__ == "__main__":
    host = os.getenv("CFI_HOST", "127.0.0.1")
    port = int(os.getenv("CFI_PORT", "8022"))
    uvicorn.run(app, host=host, port=port)

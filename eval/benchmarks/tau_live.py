"""τ-bench live task loader — optional remote fetch with honest fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

DEFAULT_TASKS = Path(__file__).resolve().parent / "tau_tasks.json"

LIVE_ASSUMPTIONS = [
    "Remote task fetch is a format adapter only; not live τ-bench execution.",
    "Tasks are compiled locally; no agent runtime is invoked.",
]


def resolve_tasks_url() -> str | None:
    return os.getenv("CFI_TAU_BENCH_URL")


def load_tasks(path: Path | None = None, *, url: str | None = None) -> list[dict[str, Any]]:
    """Load tasks from remote URL, explicit path, or bundled JSON."""
    remote = url or resolve_tasks_url()
    if remote:
        response = httpx.get(remote, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and isinstance(data.get("tasks"), list):
            return data["tasks"]
        if isinstance(data, list):
            return data
        raise ValueError("Unexpected tau-bench task payload; expected list or {tasks: [...]}")
    return json.loads((path or DEFAULT_TASKS).read_text(encoding="utf-8"))

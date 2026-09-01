#!/usr/bin/env python3
"""Health-check all CFI-Fed service apps (in-process TestClient)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from cfi_registry import RegistryStore, create_app
from services.aggregator.main import app as aggregator_app
from services.coordinator.main import app as coordinator_app
from services.replay_mock.main import app as replay_app


def main() -> int:
    checks = [
        ("registry", TestClient(create_app(RegistryStore())), "/health"),
        ("coordinator", TestClient(coordinator_app), "/health"),
        ("aggregator", TestClient(aggregator_app), None),
        ("replay_mock", TestClient(replay_app), "/health"),
    ]
    failed = []
    for name, client, path in checks:
        if path:
            resp = client.get(path)
        else:
            resp = client.post(
                "/aggregate",
                json={
                    "contributions": [],
                    "epsilon": 1.0,
                    "minimum_k": 10,
                    "measurement_spec_id": "health",
                },
            )
        ok = resp.status_code in (200, 400)
        print(f"{name}: {'OK' if ok else 'FAIL'} ({resp.status_code})")
        if not ok:
            failed.append(name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

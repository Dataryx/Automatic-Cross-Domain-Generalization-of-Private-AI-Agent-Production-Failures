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
from services.agentrx_stub.main import app as agentrx_app
from services.causalflow_stub.main import app as causalflow_app
from services.replay_mock.main import app as replay_app


def main() -> int:
    checks = [
        ("registry", TestClient(create_app(RegistryStore())), ["/health", "/ready", "/metrics"]),
        ("coordinator", TestClient(coordinator_app), ["/health", "/ready", "/metrics"]),
        ("aggregator", TestClient(aggregator_app), ["/health", "/ready", "/metrics", "/accountant"]),
        ("replay_mock", TestClient(replay_app), ["/health"]),
        ("agentrx_stub", TestClient(agentrx_app), ["/health"]),
        ("causalflow_stub", TestClient(causalflow_app), ["/health"]),
    ]
    failed = []
    for name, client, paths in checks:
        for path in paths:
            resp = client.get(path)
            ok = resp.status_code == 200
            print(f"{name}{path}: {'OK' if ok else 'FAIL'} ({resp.status_code})")
            if not ok:
                failed.append(f"{name}{path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

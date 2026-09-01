#!/usr/bin/env python3
"""Verify production observability endpoints across services."""

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
    checks: list[tuple[str, bool, str]] = []

    registry = TestClient(create_app(RegistryStore()))
    for path in ("/health", "/ready", "/metrics"):
        resp = registry.get(path)
        checks.append((f"registry{path}", resp.status_code == 200, resp.text[:120]))

    coordinator = TestClient(coordinator_app)
    for path in ("/health", "/ready", "/metrics"):
        resp = coordinator.get(path)
        checks.append((f"coordinator{path}", resp.status_code == 200, resp.text[:120]))

    aggregator = TestClient(aggregator_app)
    for path in ("/health", "/ready", "/metrics", "/accountant"):
        resp = aggregator.get(path)
        checks.append((f"aggregator{path}", resp.status_code == 200, resp.text[:120]))

    replay = TestClient(replay_app)
    resp = replay.get("/health")
    checks.append(("replay/health", resp.status_code == 200, resp.text))

    accountant = aggregator.get("/accountant").json()
    remaining = float(accountant.get("remaining_epsilon", -1))
    checks.append(("accountant_remaining_epsilon", remaining >= 0, str(remaining)))

    metrics_text = aggregator.get("/metrics").text
    checks.append(("metrics_remaining_epsilon", "cfi_remaining_epsilon" in metrics_text, metrics_text[:80]))

    failed = [name for name, ok, _ in checks if not ok]
    for name, ok, detail in checks:
        print(f"{name}: {'OK' if ok else 'FAIL'} ({detail})")
    if failed:
        print(f"Failed checks: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("Observability verification OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

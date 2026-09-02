"""Coordinator client tests."""

from cfi_federation.coordinator_client import CoordinatorClient
from services.coordinator.main import app as coordinator_app


def test_coordinator_consortium_round() -> None:
    client = CoordinatorClient.for_app(coordinator_app)
    result = client.consortium_round(tenants=12, minimum_k=10, seed=421337)
    assert result.get("released") is True
    assert result.get("participants", 0) >= 10

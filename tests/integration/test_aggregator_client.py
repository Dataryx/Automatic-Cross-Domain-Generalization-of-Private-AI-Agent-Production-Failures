"""Aggregator client tests."""

from cfi_federation import ClippedContribution
from cfi_federation.aggregator_client import AggregatorClient
from services.aggregator.main import app as aggregator_app


def test_aggregator_client_round_trip() -> None:
    client = AggregatorClient.for_app(aggregator_app)
    contribs = [
        ClippedContribution(tenant_id=f"t{i}", failures=1, trials=3, coverage=1.0) for i in range(5)
    ]
    result = client.aggregate(
        contribs,
        epsilon=1.0,
        minimum_k=5,
        measurement_spec_id="test-spec",
        cohort_id="test-cohort",
    )
    assert result.get("released") is True

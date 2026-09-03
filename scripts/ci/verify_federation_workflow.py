#!/usr/bin/env python3
"""Federation workflow: publish -> multi-tenant contribute -> DP aggregate."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typer.testing import CliRunner

from cfi_cli import contribute_app
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation.aggregator_client import AggregatorClient
from cfi_recipient.federation_contrib import contribute_from_package
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient
from services.aggregator.main import app as aggregator_app


def _manifest(invariant_id: str) -> CohortManifest:
    spec = MeasurementSpec(
        spec_id="federation-workflow",
        invariant_id=invariant_id,
        simulated_user="stub",
        tool_behavior="stubbed",
        judge="state_first",
        evidence_bar="high",
        trial_count=3,
        aggregation_rule="mean",
        compiler_version="0.1.0",
    )
    return CohortManifest(
        invariant_id=invariant_id,
        eligible_compiler_versions=["0.1.0"],
        measurement_spec=spec,
        trial_count=3,
        clipping_f=10,
        clipping_n=100,
        privacy_budget_epsilon=1.0,
        aggregation_epoch="federation-workflow",
        expiration="2026-12-31",
        minimum_cohort_k=5,
    )


def main() -> int:
    invariant_id = build_exception_precedence_cfi().id
    registry_app = create_app(RegistryStore())

    def registry_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(registry_app)
        return RegistryClient(base_url, token=token)

    import cfi_registry.client as client_module

    original_registry = client_module.RegistryClient
    client_module.RegistryClient = registry_factory  # type: ignore[misc,assignment]

    with tempfile.TemporaryDirectory() as tmp:
        runner = CliRunner()
        publish = runner.invoke(
            contribute_app,
            ["publish", "--output", str(Path(tmp) / "published.json"), "--registry-url", "http://test"],
        )
        client_module.RegistryClient = original_registry  # type: ignore[misc,assignment]
        if publish.exit_code != 0:
            print(publish.stdout, publish.stderr, file=sys.stderr)
            return 1

    package = RegistryClient.for_app(registry_app).get_cfi(invariant_id)
    manifest = _manifest(invariant_id)
    contributions = []
    domains = ["procurement", "healthcare", "data_operations", "finance", "logistics"]
    for idx, domain in enumerate(domains):
        tenant = f"tenant-{idx:02d}"
        fed = contribute_from_package(
            package,
            domain=domain,
            tenant_id=tenant,
            manifest=manifest,
            roles=build_exception_precedence_cfi().required_mapping_roles,
        )
        assert fed.share_envelope["schema"] == "share-envelope/1.0"
        contributions.append(fed.contribution)

    aggregator = AggregatorClient.for_app(aggregator_app)
    release = aggregator.aggregate(
        contributions,
        epsilon=1.0,
        minimum_k=5,
        measurement_spec_id=manifest.measurement_spec.spec_id,
        cohort_id=manifest.aggregation_epoch,
    )
    if not release.get("released"):
        print(f"Aggregate not released: {release}", file=sys.stderr)
        return 1

    print(
        f"Federation workflow OK: {invariant_id} "
        f"prevalence={release.get('noisy_prevalence')} tenants={len(contributions)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

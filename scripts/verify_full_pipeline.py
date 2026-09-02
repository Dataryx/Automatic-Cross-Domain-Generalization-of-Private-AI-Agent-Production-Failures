#!/usr/bin/env python3
"""Full CFI-Fed pipeline: publish -> assess -> federate -> consortium round."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typer.testing import CliRunner

from cfi_cli import contribute_app, recipient_app
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation.aggregator_client import AggregatorClient
from cfi_federation.coordinator_client import CoordinatorClient
from cfi_recipient.federation_contrib import contribute_from_package
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient
from services.aggregator.main import app as aggregator_app
from services.coordinator.main import app as coordinator_app


def _manifest(invariant_id: str) -> CohortManifest:
    spec = MeasurementSpec(
        spec_id="full-pipeline",
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
        aggregation_epoch="full-pipeline",
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
        tmp_path = Path(tmp)
        runner = CliRunner()
        publish = runner.invoke(
            contribute_app,
            ["publish", "--output", str(tmp_path / "published.json"), "--registry-url", "http://test"],
        )
        assess = runner.invoke(
            recipient_app,
            [
                "assess",
                "--invariant-id",
                invariant_id,
                "--registry-url",
                "http://test",
                "--output",
                str(tmp_path / "assess.json"),
            ],
        )
        client_module.RegistryClient = original_registry  # type: ignore[misc,assignment]

        if publish.exit_code != 0 or assess.exit_code != 0:
            print(publish.stdout, publish.stderr, assess.stdout, assess.stderr, file=sys.stderr)
            return 1

        assess_report = json.loads((tmp_path / "assess.json").read_text(encoding="utf-8"))
        if "agent_susceptibility" not in assess_report.get("metrics", {}):
            print("Assessment missing susceptibility metric", file=sys.stderr)
            return 1

    package = RegistryClient.for_app(registry_app).get_cfi(invariant_id)
    manifest = _manifest(invariant_id)
    domains = ["procurement", "healthcare", "data_operations", "finance", "logistics"]
    contributions = []
    for idx, domain in enumerate(domains):
        fed = contribute_from_package(
            package,
            domain=domain,
            tenant_id=f"tenant-{idx:02d}",
            manifest=manifest,
            roles=build_exception_precedence_cfi().required_mapping_roles,
        )
        contributions.append(fed.contribution)

    aggregator = AggregatorClient.for_app(aggregator_app)
    aggregate = aggregator.aggregate(
        contributions,
        epsilon=1.0,
        minimum_k=5,
        measurement_spec_id=manifest.measurement_spec.spec_id,
        cohort_id=manifest.aggregation_epoch,
    )
    if not aggregate.get("released"):
        print(f"Aggregate not released: {aggregate}", file=sys.stderr)
        return 1

    coordinator = CoordinatorClient.for_app(coordinator_app)
    consortium = coordinator.consortium_round(tenants=12, minimum_k=10, seed=421337)
    if not consortium.get("released"):
        print(f"Consortium round not released: {consortium}", file=sys.stderr)
        return 1

    summary = {
        "invariant_id": invariant_id,
        "assessed": True,
        "aggregate_prevalence": aggregate.get("noisy_prevalence"),
        "consortium_participants": consortium.get("participants"),
        "consortium_prevalence": consortium.get("noisy_prevalence"),
        "assumptions": [
            "Full pipeline smoke uses in-process services; not a production deployment proof.",
            "Raw incident evidence never crosses contributor boundary in this workflow.",
        ],
    }
    out = ROOT / "eval" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "full_pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Full pipeline OK: {json.dumps(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

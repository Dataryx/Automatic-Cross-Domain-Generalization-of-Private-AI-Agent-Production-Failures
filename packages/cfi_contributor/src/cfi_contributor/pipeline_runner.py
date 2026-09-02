"""Full CFI-Fed pipeline orchestration for smoke tests and remote CLI runs."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from cfi_cli import contribute_app, recipient_app
from cfi_contributor.agent_hooks import probe_all_profiles_http
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation.aggregator_client import AggregatorClient
from cfi_federation.coordinator_client import CoordinatorClient
from cfi_recipient.federation_contrib import contribute_from_package
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def cohort_manifest(invariant_id: str, *, epoch: str) -> CohortManifest:
    spec = MeasurementSpec(
        spec_id=epoch,
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
        aggregation_epoch=epoch,
        expiration="2026-12-31",
        minimum_cohort_k=5,
    )


def run_remote_full_pipeline(
    endpoints: dict[str, str],
    *,
    epoch: str,
    probe_hooks: bool = True,
    extra_assumptions: list[str] | None = None,
) -> dict[str, object]:
    """Publish, assess, federate, and consortium round against live HTTP endpoints."""
    invariant_id = build_exception_precedence_cfi().id
    registry_url = endpoints["registry"]
    aggregator_url = endpoints["aggregator"]
    coordinator_url = endpoints["coordinator"]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        runner = CliRunner()
        publish = runner.invoke(
            contribute_app,
            ["publish", "--output", str(tmp_path / "published.json"), "--registry-url", registry_url],
        )
        assess = runner.invoke(
            recipient_app,
            [
                "assess",
                "--invariant-id",
                invariant_id,
                "--registry-url",
                registry_url,
                "--domain",
                "procurement",
                "--output",
                str(tmp_path / "assess.json"),
            ],
        )
        if publish.exit_code != 0 or assess.exit_code != 0:
            raise RuntimeError(
                f"CLI failed publish={publish.exit_code} assess={assess.exit_code}\n"
                f"{publish.stdout}{publish.stderr}{assess.stdout}{assess.stderr}"
            )

        assess_report = json.loads((tmp_path / "assess.json").read_text(encoding="utf-8"))
        if "agent_susceptibility" not in assess_report.get("metrics", {}):
            raise RuntimeError("Assessment missing agent_susceptibility metric")

    with RegistryClient(registry_url) as registry:
        package = registry.get_cfi(invariant_id)

    manifest = cohort_manifest(invariant_id, epoch=epoch)
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

    with AggregatorClient(aggregator_url) as aggregator:
        aggregate = aggregator.aggregate(
            contributions,
            epsilon=1.0,
            minimum_k=5,
            measurement_spec_id=manifest.measurement_spec.spec_id,
            cohort_id=manifest.aggregation_epoch,
        )
    if not aggregate.get("released"):
        raise RuntimeError(f"Aggregate not released: {aggregate}")

    with CoordinatorClient(coordinator_url) as coordinator:
        consortium = coordinator.consortium_round(tenants=12, minimum_k=10, seed=421337)
    if not consortium.get("released"):
        raise RuntimeError(f"Consortium round not released: {consortium}")

    hook_profiles: list[str] = []
    if probe_hooks:
        hook_results = probe_all_profiles_http()
        failed_hooks = [r.profile for r in hook_results if not (r.healthy and r.replay_ok)]
        if failed_hooks:
            raise RuntimeError(f"Agent hook probes failed: {failed_hooks}")
        hook_profiles = [r.profile for r in hook_results]

    assumptions = [
        "Remote full pipeline uses live HTTP against running services.",
        "Raw incident evidence never crosses contributor boundary in this workflow.",
    ]
    if probe_hooks:
        assumptions.append("AgentRx/CausalFlow hooks are sandbox stubs, not production agent runtimes.")
    if extra_assumptions:
        assumptions.extend(extra_assumptions)

    summary: dict[str, object] = {
        "invariant_id": invariant_id,
        "registry_url": registry_url,
        "assessed": True,
        "aggregate_prevalence": aggregate.get("noisy_prevalence"),
        "consortium_participants": consortium.get("participants"),
        "consortium_prevalence": consortium.get("noisy_prevalence"),
        "assumptions": assumptions,
    }
    if hook_profiles:
        summary["hook_profiles"] = hook_profiles
    return summary


def run_inprocess_full_pipeline(
    *,
    epoch: str = "full-pipeline",
    extra_assumptions: list[str] | None = None,
) -> dict[str, object]:
    """Full pipeline smoke using in-process TestClient-backed services."""
    from services.aggregator.main import app as aggregator_app
    from services.coordinator.main import app as coordinator_app

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
            raise RuntimeError(
                f"CLI failed publish={publish.exit_code} assess={assess.exit_code}\n"
                f"{publish.stdout}{publish.stderr}{assess.stdout}{assess.stderr}"
            )

        assess_report = json.loads((tmp_path / "assess.json").read_text(encoding="utf-8"))
        if "agent_susceptibility" not in assess_report.get("metrics", {}):
            raise RuntimeError("Assessment missing agent_susceptibility metric")

    package = RegistryClient.for_app(registry_app).get_cfi(invariant_id)
    manifest = cohort_manifest(invariant_id, epoch=epoch)
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
        raise RuntimeError(f"Aggregate not released: {aggregate}")

    coordinator = CoordinatorClient.for_app(coordinator_app)
    consortium = coordinator.consortium_round(tenants=12, minimum_k=10, seed=421337)
    if not consortium.get("released"):
        raise RuntimeError(f"Consortium round not released: {consortium}")

    assumptions = [
        "Full pipeline smoke uses in-process services; not a production deployment proof.",
        "Raw incident evidence never crosses contributor boundary in this workflow.",
    ]
    if extra_assumptions:
        assumptions.extend(extra_assumptions)

    return {
        "invariant_id": invariant_id,
        "assessed": True,
        "aggregate_prevalence": aggregate.get("noisy_prevalence"),
        "consortium_participants": consortium.get("participants"),
        "consortium_prevalence": consortium.get("noisy_prevalence"),
        "assumptions": assumptions,
    }

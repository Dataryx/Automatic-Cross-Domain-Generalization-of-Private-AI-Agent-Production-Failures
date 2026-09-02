"""CLI endpoint default tests."""

import json

from typer.testing import CliRunner

from cfi_cli import contribute_app
from cfi_contributor.service_urls import all_endpoint_env, default_registry_url


def test_endpoints_command() -> None:
    runner = CliRunner()
    result = runner.invoke(contribute_app, ["endpoints"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["registry"] == all_endpoint_env()["registry"]


def test_default_registry_url_env(monkeypatch) -> None:
    monkeypatch.setenv("CFI_REGISTRY_URL", "http://custom-registry:7000")
    assert default_registry_url() == "http://custom-registry:7000"


def test_run_pipeline_cli(monkeypatch) -> None:
    from typer.testing import CliRunner

    from cfi_cli import contribute_app

    def fake_pipeline(endpoints: dict[str, str], *, epoch: str, probe_hooks: bool = True, extra_assumptions=None):
        return {
            "invariant_id": "CFI-TEST",
            "registry_url": endpoints["registry"],
            "assessed": True,
            "aggregate_prevalence": 1.0,
            "consortium_prevalence": 1.0,
        }

    monkeypatch.setattr("cfi_contributor.pipeline_runner.run_remote_full_pipeline", fake_pipeline)
    runner = CliRunner()
    result = runner.invoke(contribute_app, ["run-pipeline", "--no-probe-hooks"])
    assert result.exit_code == 0
    assert "CFI-TEST" in result.stdout

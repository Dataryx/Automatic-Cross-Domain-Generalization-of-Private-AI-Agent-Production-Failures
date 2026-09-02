"""Cross-boundary contributor->registry->recipient smoke."""

from pathlib import Path

from typer.testing import CliRunner

from cfi_cli import contribute_app, recipient_app
from cfi_core.examples import build_exception_precedence_cfi
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def test_cross_boundary_publish_fetch(tmp_path: Path, monkeypatch) -> None:
    app = create_app(RegistryStore())
    invariant_id = build_exception_precedence_cfi().id

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    monkeypatch.setattr("cfi_registry.client.RegistryClient", client_factory)
    runner = CliRunner()
    published = tmp_path / "published.json"
    fetched = tmp_path / "fetched.json"
    publish = runner.invoke(
        contribute_app,
        ["publish", "--output", str(published), "--registry-url", "http://test"],
    )
    fetch = runner.invoke(
        recipient_app,
        [
            "fetch",
            "--invariant-id",
            invariant_id,
            "--output",
            str(fetched),
            "--registry-url",
            "http://test",
        ],
    )
    assert publish.exit_code == 0, publish.stdout + publish.stderr
    assert fetch.exit_code == 0, fetch.stdout + fetch.stderr
    assert fetched.exists()


def test_recipient_pull_compiles(tmp_path: Path, monkeypatch) -> None:
    app = create_app(RegistryStore())
    invariant_id = build_exception_precedence_cfi().id

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    monkeypatch.setattr("cfi_registry.client.RegistryClient", client_factory)
    runner = CliRunner()
    publish = runner.invoke(
        contribute_app,
        ["publish", "--output", str(tmp_path / "published.json"), "--registry-url", "http://test"],
    )
    assert publish.exit_code == 0
    pull = runner.invoke(
        recipient_app,
        ["pull", "--invariant-id", invariant_id, "--registry-url", "http://test", "--domain", "procurement"],
    )
    assert pull.exit_code == 0, pull.stdout + pull.stderr
    assert "compiled" in pull.stdout.lower()

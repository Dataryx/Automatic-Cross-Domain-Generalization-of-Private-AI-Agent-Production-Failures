"""End-to-end contributor publish -> recipient assess."""

from pathlib import Path

from typer.testing import CliRunner

from cfi_cli import contribute_app, recipient_app
from cfi_core.examples import build_exception_precedence_cfi
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def test_publish_then_assess(tmp_path: Path, monkeypatch) -> None:
    app = create_app(RegistryStore())
    invariant_id = build_exception_precedence_cfi().id

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    monkeypatch.setattr("cfi_registry.client.RegistryClient", client_factory)
    runner = CliRunner()
    published = tmp_path / "published.json"
    report = tmp_path / "assess.json"
    publish = runner.invoke(
        contribute_app,
        ["publish", "--output", str(published), "--registry-url", "http://test"],
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
            str(report),
        ],
    )
    assert publish.exit_code == 0, publish.stdout + publish.stderr
    assert assess.exit_code == 0, assess.stdout + assess.stderr
    assert report.exists()

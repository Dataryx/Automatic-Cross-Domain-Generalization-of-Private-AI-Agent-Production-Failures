"""Contribute publish CLI tests."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cfi_cli import contribute_app
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def test_contribute_publish_cli(tmp_path: Path, monkeypatch) -> None:
    app = create_app(RegistryStore())

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    monkeypatch.setattr("cfi_registry.client.RegistryClient", client_factory)
    output = tmp_path / "published.json"
    result = CliRunner().invoke(
        contribute_app,
        ["publish", "--output", str(output), "--registry-url", "http://test"],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    package = json.loads(output.read_text(encoding="utf-8"))
    assert package["id"] in result.stdout

"""Registry audit CLI tests."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cfi_cli import registry_app
from cfi_governance.audit_attestation import sign_audit_export
from cfi_core.signing import KeyPair


def test_registry_audit_verify_command(tmp_path: Path) -> None:
    signed = sign_audit_export(
        {"events": [{"action": "cfi.registered"}], "watermark": 0, "exported_at": "t"},
        KeyPair.generate("cli-audit"),
    )
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(signed), encoding="utf-8")
    result = CliRunner().invoke(registry_app, ["audit-verify", str(path)])
    assert result.exit_code == 0
    assert "valid" in result.stdout

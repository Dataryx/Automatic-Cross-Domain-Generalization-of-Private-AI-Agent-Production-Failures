"""Signed audit export batches for external verification."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cfi_core.signing import KeyPair
from cfi_governance.release_attestation import (
    load_release_key_pair,
    sign_release_manifest,
    verify_release_manifest,
)


def load_audit_key_pair() -> KeyPair:
    """Load audit signing key; falls back to release signing key configuration."""
    org_id = os.getenv("CFI_AUDIT_SIGNING_ORG", os.getenv("CFI_RELEASE_SIGNING_ORG", "cfi-fed-audit"))
    pem = os.getenv("CFI_AUDIT_SIGNING_KEY_PEM")
    if pem:
        return KeyPair.from_private_pem(pem, org_id)
    key_path = os.getenv("CFI_AUDIT_SIGNING_KEY_PATH")
    if key_path:
        return KeyPair.from_private_pem(Path(key_path).read_text(encoding="utf-8"), org_id)
    return load_release_key_pair()


def sign_audit_export(export: dict[str, Any], key_pair: KeyPair | None = None) -> dict[str, Any]:
    return sign_release_manifest(export, key_pair or load_audit_key_pair())


def verify_audit_export(signed_export: dict[str, Any]) -> bool:
    return verify_release_manifest(signed_export)

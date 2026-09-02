"""Signed release manifest attestation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cfi_core.signing import KeyPair, Signer, Verifier


def load_release_key_pair() -> KeyPair:
    """Load stable signing key from env or generate ephemeral research key."""
    org_id = os.getenv("CFI_RELEASE_SIGNING_ORG", "cfi-fed-release")
    pem = os.getenv("CFI_RELEASE_SIGNING_KEY_PEM")
    if pem:
        return KeyPair.from_private_pem(pem, org_id)
    key_path = os.getenv("CFI_RELEASE_SIGNING_KEY_PATH")
    if key_path:
        return KeyPair.from_private_pem(Path(key_path).read_text(encoding="utf-8"), org_id)
    return KeyPair.generate(org_id)


def sign_release_manifest(manifest: dict[str, Any], key_pair: KeyPair) -> dict[str, Any]:
    """Return manifest with Ed25519 signature and certificate chain."""
    payload = {k: v for k, v in manifest.items() if k not in ("signature", "certificate_chain")}
    signature, chain = Signer(key_pair).sign_package(payload)
    signed = dict(payload)
    signed["signature"] = signature
    signed["certificate_chain"] = chain
    return signed


def verify_release_manifest(signed_manifest: dict[str, Any]) -> bool:
    return Verifier().verify(signed_manifest)

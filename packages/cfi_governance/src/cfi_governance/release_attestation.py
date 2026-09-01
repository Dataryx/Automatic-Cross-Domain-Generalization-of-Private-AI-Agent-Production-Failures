"""Signed release manifest attestation."""

from __future__ import annotations

from typing import Any

from cfi_core.signing import KeyPair, Signer, Verifier


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

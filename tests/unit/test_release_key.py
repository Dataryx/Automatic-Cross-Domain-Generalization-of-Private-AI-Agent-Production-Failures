"""Stable release signing key tests."""

from cfi_core.signing import KeyPair
from cfi_governance.release_attestation import load_release_key_pair, sign_release_manifest, verify_release_manifest


def test_load_release_key_pair_from_pem(monkeypatch) -> None:
    key_pair = KeyPair.generate("stable-release")
    monkeypatch.setenv("CFI_RELEASE_SIGNING_KEY_PEM", key_pair.private_pem())
    monkeypatch.setenv("CFI_RELEASE_SIGNING_ORG", "stable-release")
    loaded = load_release_key_pair()
    manifest = {"version": "0.1.0"}
    signed_a = sign_release_manifest(manifest, loaded)
    signed_b = sign_release_manifest(manifest, key_pair)
    assert signed_a["signature"] == signed_b["signature"]
    assert verify_release_manifest(signed_a)

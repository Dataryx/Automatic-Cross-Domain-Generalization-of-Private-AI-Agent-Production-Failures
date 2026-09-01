"""Release attestation tests."""

from cfi_core.signing import KeyPair
from cfi_governance.release_attestation import sign_release_manifest, verify_release_manifest


def test_sign_and_verify_release_manifest() -> None:
    manifest = {"package": "cfi-fed", "version": "0.1.0", "pytest_exit_code": 0}
    signed = sign_release_manifest(manifest, KeyPair.generate("release-test"))
    assert "signature" in signed
    assert "certificate_chain" in signed
    assert verify_release_manifest(signed)


def test_tampered_release_manifest_fails() -> None:
    signed = sign_release_manifest({"version": "0.1.0"}, KeyPair.generate("release-test"))
    signed["version"] = "0.2.0"
    assert not verify_release_manifest(signed)

"""ZK attestation module tests."""

from cfi_federation.zk_attestation import prove_circuit_execution, verify_circuit_attestation


def test_zk_attestation_roundtrip() -> None:
    att = prove_circuit_execution({"failures": 3, "trials": 10, "clip_f": 5, "clip_n": 50})
    assert verify_circuit_attestation(att)
    assert "stochastic" in att.assumptions[1].lower() or "deterministic" in att.assumptions[0].lower()

"""ZK attestation module tests."""

from cfi_federation.zk_attestation import prove_circuit_execution, verify_circuit_attestation


def test_zk_attestation_roundtrip() -> None:
    att = prove_circuit_execution({"failures": 3, "trials": 10, "clip_f": 5, "clip_n": 50})
    assert verify_circuit_attestation(att)
    assert "stochastic" in att.assumptions[1].lower() or "deterministic" in att.assumptions[0].lower()


def test_zk_attestation_json_roundtrip() -> None:
    from cfi_federation.zk_attestation import attestation_from_json, attestation_to_json, build_aggregate_attestation

    att = prove_circuit_execution({"failures": 1, "trials": 3, "clip_f": 10, "clip_n": 100})
    restored = attestation_from_json(attestation_to_json(att))
    assert verify_circuit_attestation(restored)

    class _Contrib:
        failures = 2
        trials = 4

    agg = build_aggregate_attestation([_Contrib(), _Contrib()], clip_f=10, clip_n=100)
    assert verify_circuit_attestation(agg)

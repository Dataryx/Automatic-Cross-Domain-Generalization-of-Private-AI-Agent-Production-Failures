"""Optional zero-knowledge attestation for deterministic measurement circuits.

LIMITATION: ZK attestation can prove execution of a fixed deterministic circuit.
It CANNOT generally prove that a complex stochastic agent evaluation faithfully
represents an organization's production environment.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class CircuitAttestation:
    circuit_digest: str
    input_digest: str
    output_digest: str
    proof: bytes
    assumptions: list[str] = field(default_factory=lambda: [
        "Proves deterministic circuit execution only.",
        "Does not attest stochastic agent evaluation fidelity.",
    ])


def deterministic_circuit(inputs: dict[str, int]) -> dict[str, int]:
    """Example fixed circuit: clipped failure count."""
    failures = min(inputs.get("failures", 0), inputs.get("clip_f", 10))
    trials = min(inputs.get("trials", 0), inputs.get("clip_n", 100))
    return {"failures": failures, "trials": trials}


def prove_circuit_execution(inputs: dict[str, int]) -> CircuitAttestation:
    """Placeholder proof — production would use a ZK backend."""
    outputs = deterministic_circuit(inputs)
    circuit_digest = hashlib.sha256(b"cfi-fed/clipped-count/v1").hexdigest()
    input_digest = hashlib.sha256(repr(sorted(inputs.items())).encode()).hexdigest()
    output_digest = hashlib.sha256(repr(sorted(outputs.items())).encode()).hexdigest()
    proof = hashlib.sha256((circuit_digest + input_digest + output_digest).encode()).digest()
    return CircuitAttestation(
        circuit_digest=circuit_digest,
        input_digest=input_digest,
        output_digest=output_digest,
        proof=proof,
    )


def verify_circuit_attestation(attestation: CircuitAttestation) -> bool:
    expected = hashlib.sha256(
        (attestation.circuit_digest + attestation.input_digest + attestation.output_digest).encode()
    ).digest()
    return attestation.proof == expected


def attestation_to_json(attestation: CircuitAttestation) -> dict[str, object]:
    """Serialize attestation for JSON HTTP payloads (proof as hex)."""
    return {
        "circuit_digest": attestation.circuit_digest,
        "input_digest": attestation.input_digest,
        "output_digest": attestation.output_digest,
        "proof": attestation.proof.hex(),
        "assumptions": list(attestation.assumptions),
    }


def attestation_from_json(data: dict[str, object]) -> CircuitAttestation:
    """Deserialize attestation from JSON HTTP payloads."""
    proof = data["proof"]
    if isinstance(proof, str):
        proof_bytes = bytes.fromhex(proof)
    elif isinstance(proof, (bytes, bytearray)):
        proof_bytes = bytes(proof)
    else:
        raise TypeError("attestation proof must be hex string or bytes")
    assumptions = data.get("assumptions", [])
    return CircuitAttestation(
        circuit_digest=str(data["circuit_digest"]),
        input_digest=str(data["input_digest"]),
        output_digest=str(data["output_digest"]),
        proof=proof_bytes,
        assumptions=list(assumptions) if isinstance(assumptions, list) else [],
    )


def build_aggregate_attestation(
    contributions: list[object],
    *,
    clip_f: int,
    clip_n: int,
) -> CircuitAttestation:
    """Build ZK attestation over clipped aggregate counts (deterministic circuit only)."""
    failures = sum(getattr(c, "failures", 0) for c in contributions)
    trials = sum(getattr(c, "trials", 0) for c in contributions)
    return prove_circuit_execution(
        {"failures": failures, "trials": trials, "clip_f": clip_f, "clip_n": clip_n}
    )

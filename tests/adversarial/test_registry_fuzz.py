"""Registry adversarial fuzz corpus — malformed packages rejected without partial persistence."""

import copy

import pytest

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair, Signer
from cfi_registry import RegistryStore


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    answers = {i: True for i in range(1, 13)}
    verdict = gate.run(cfi, answers, adversary_scores={"source_attribution": 0.07, "reconstruction": 0.1})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    key = KeyPair.generate("fuzz-org")
    result = Packager(key).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: {**p, "prompt": "leaked"},
        lambda p: {**p, "signature": "invalid"},
        lambda p: {**{k: v for k, v in p.items() if k != "signature"}, "signature": None},
        lambda p: {**p, "nodes": p["nodes"] * 1000},
        lambda p: {**p, "id": ""},
        lambda p: {**p, "failure_predicate": "refund customer now"},
    ],
)
def test_registry_rejects_adversarial_packages(mutation) -> None:
    store = RegistryStore()
    good = _signed_package()
    bad = mutation(copy.deepcopy(good))
    with pytest.raises(ValueError):
        store.register(bad)


def test_registry_rejects_duplicate() -> None:
    store = RegistryStore()
    pkg = _signed_package()
    store.register(pkg)
    with pytest.raises(ValueError):
        store.register(pkg)


def test_registry_no_partial_persistence_on_failure() -> None:
    store = RegistryStore()
    pkg = _signed_package()
    store.register(pkg)
    bad = copy.deepcopy(pkg)
    bad["nodes"] = []
    with pytest.raises(ValueError):
        store.register(bad)
    assert store.get(pkg["id"])["id"] == pkg["id"]

#!/usr/bin/env python3
"""Run all Section 7.2 red-team adversaries and emit a signed report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cfi_contributor.adversaries import ReleaseGateAdversaries
from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_federation import shamir_share
from eval.redteam.harness import (
    ADVERSARY_RUNNERS,
    collusion_reveal,
    external_observer_timing,
    honest_but_curious_registry,
    malicious_contributor,
    malicious_recipient_probe,
    model_provider_traffic,
    sybil_organizations,
)

OUT = Path(__file__).resolve().parent / "output"


def _signed_cfi() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("redteam-contributor")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pkg = _signed_cfi()
    adv = ReleaseGateAdversaries().score_cfi(build_exception_precedence_cfi())

    results = [
        honest_but_curious_registry([pkg]).__dict__,
        malicious_recipient_probe(pkg).__dict__,
        malicious_contributor(pkg).__dict__,
        sybil_organizations(["org-a", "org-a", "org-b"], cap=1).__dict__,
        collusion_reveal(shamir_share(42, 2, 3), threshold=2).__dict__,
        external_observer_timing(["public-event"], ["other-event"]).__dict__,
        model_provider_traffic(["stub_po"], ["stub_po", "real_api"]).__dict__,
        {
            "adversary": "release_gate_attribution",
            "success_rate": adv.source_attribution,
            "metric": "source_attribution",
            "notes": adv.notes,
        },
        {
            "adversary": "release_gate_reconstruction",
            "success_rate": adv.reconstruction,
            "metric": "reconstruction",
            "notes": adv.notes,
        },
    ]

    report = {
        "adversary_count": len(ADVERSARY_RUNNERS) + 2,
        "results": results,
        "assumptions": [
            "Heuristic adversaries; not a formal privacy audit.",
            "Canonical CFI should score low on attribution/reconstruction.",
        ],
    }
    (OUT / "redteam_report.json").write_text(json.dumps(report, indent=2))
    print(f"Red-team report: {len(results)} adversary results -> {OUT / 'redteam_report.json'}")


if __name__ == "__main__":
    main()

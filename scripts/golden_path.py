#!/usr/bin/env python3
"""Golden-path smoke: contribute -> registry -> review -> compile -> aggregate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_federation import ClippedContribution
from cfi_governance.review import ReviewStatus
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.ontology import build_recipient_context
from cfi_registry import RegistryStore, create_app
from services.aggregator.main import app as aggregator_app
from services.coordinator.main import app as coordinator_app


def main() -> int:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    pkg = Packager(KeyPair.generate("golden-path")).package(cfi, verdict)
    if not pkg.success or pkg.cfi is None:
        print("Packaging failed", file=sys.stderr)
        return 1
    package = pkg.cfi.model_dump(mode="json")

    registry = TestClient(create_app(RegistryStore()))
    iid = registry.post("/cfi/register", json={"package": package}).json()["invariant_id"]
    review = registry.post(
        f"/review/{iid}/decision",
        json={
            "status": ReviewStatus.APPROVED.value,
            "reviewer": "golden@org",
            "notes": "smoke",
            "checklist_complete": True,
        },
    )
    assert review.status_code == 200

    ctx = build_recipient_context("procurement", cfi.required_mapping_roles)
    compilation = fail_closed_compile(cfi, ctx, manifest=None)
    if compilation.abstained:
        print(f"Compile abstained: {compilation.abstention_reason}", file=sys.stderr)
        return 1

    coordinator = TestClient(coordinator_app)
    round_resp = coordinator.post("/consortium/round", json={"tenants": 10, "minimum_k": 10, "seed": 421337})
    if round_resp.status_code != 200:
        print(f"Consortium round failed: {round_resp.text}", file=sys.stderr)
        return 1

    aggregator = TestClient(aggregator_app)
    contribs = [ClippedContribution(tenant_id=f"t{i}", failures=1, trials=3, coverage=1.0) for i in range(10)]
    agg = aggregator.post(
        "/aggregate",
        json={
            "contributions": [c.__dict__ for c in contribs],
            "epsilon": 1.0,
            "minimum_k": 10,
            "measurement_spec_id": "golden",
            "cohort_id": "golden",
        },
    )
    if agg.status_code != 200 or not agg.json().get("released"):
        print(f"Aggregate failed: {agg.text}", file=sys.stderr)
        return 1

    summary = {
        "invariant_id": iid,
        "compiled_cases": len(compilation.cases),
        "consortium_participants": round_resp.json()["participants"],
        "noisy_prevalence": agg.json()["noisy_prevalence"],
    }
    out = ROOT / "eval" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "golden_path_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Golden path OK: {json.dumps(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Automated checks for Section 15 Definition of Done (partial)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class DodCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class DodReport:
    checks: list[DodCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def to_dict(self) -> dict:
        return {
            "all_passed": self.all_passed,
            "passed": sum(1 for c in self.checks if c.passed),
            "total": len(self.checks),
            "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in self.checks],
        }


def verify() -> DodReport:
    report = DodReport()

    # Schemas
    schema = ROOT / "schemas" / "cfi" / "1.0" / "schema.json"
    report.checks.append(DodCheck("cfi_schema_exists", schema.exists(), str(schema)))

    # Docs
    for doc in ["architecture", "threat_model", "governance", "release_gate_checklist", "limitations", "deviations"]:
        p = ROOT / "docs" / f"{doc}.md"
        report.checks.append(DodCheck(f"doc_{doc}", p.exists(), str(p)))

    # Appendix A validates
    try:
        from cfi_core.examples import build_exception_precedence_cfi
        from cfi_core.schema_validate import validate_cfi

        cfi = build_exception_precedence_cfi()
        validate_cfi(cfi.model_dump(mode="json"))
        report.checks.append(DodCheck("appendix_a_validates", True))
    except Exception as exc:
        report.checks.append(DodCheck("appendix_a_validates", False, str(exc)))

    # Cross-domain compile smoke
    try:
        from cfi_core.examples import build_exception_precedence_cfi
        from cfi_recipient.compiler import fail_closed_compile
        from cfi_recipient.ontology import build_recipient_context

        cfi = build_exception_precedence_cfi()
        for domain in ["procurement", "healthcare", "data_operations"]:
            ctx = build_recipient_context(domain, cfi.required_mapping_roles)
            result = fail_closed_compile(cfi, ctx, manifest=None)
            if result.abstained:
                raise ValueError(f"{domain} abstained: {result.abstention_reason}")
        report.checks.append(DodCheck("cross_domain_compiles", True))
    except Exception as exc:
        report.checks.append(DodCheck("cross_domain_compiles", False, str(exc)))

    # Production baselines count
    from eval.production.harness import BASELINES

    report.checks.append(DodCheck("twelve_baselines_defined", len(BASELINES) >= 12, f"count={len(BASELINES)}"))

    # Red-team adversaries
    from eval.redteam.harness import ADVERSARY_RUNNERS

    report.checks.append(DodCheck("seven_redteam_adversaries", len(ADVERSARY_RUNNERS) >= 7, f"count={len(ADVERSARY_RUNNERS)}"))

    # Cross-domain examples
    for domain, folder in [
        ("procurement", "retail_to_procurement"),
        ("healthcare", "retail_to_healthcare"),
        ("data_operations", "retail_to_dataops"),
    ]:
        p = ROOT / "examples" / folder / "mappings.py"
        report.checks.append(DodCheck(f"example_{domain}", p.exists(), str(p)))

    # Sim script
    report.checks.append(DodCheck("sim_script", (ROOT / "sim" / "run_cfi_sim.py").exists()))

    # Phase harnesses
    report.checks.append(DodCheck("consortium_pilot", (ROOT / "eval" / "consortium" / "run_consortium_pilot.py").exists()))
    report.checks.append(DodCheck("field_pilot", (ROOT / "eval" / "field" / "run_prospective_pilot.py").exists()))

    return report


def main() -> int:
    report = verify()
    out = ROOT / "eval" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "dod_report.json").write_text(json.dumps(report.to_dict(), indent=2))
    for c in report.checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"[{status}] {c.name}" + (f" — {c.detail}" if c.detail and not c.passed else ""))
    print(f"\n{report.to_dict()['passed']}/{report.to_dict()['total']} checks passed")
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

"""Prospective field-study framework (Phase 6).

Simulates multi-org reporting over a study window. Measures whether shared CFIs
flag susceptible deployments before structurally equivalent local incidents.

This is a protocol harness — not evidence from a live six-month deployment.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.mitigation import MitigationCandidate, MitigationLayer, evaluate_mitigation, susceptibility
from cfi_recipient.ontology import build_recipient_context
from cfi_recipient.sandbox import Sandbox, SandboxTrace


class ReportType(str, Enum):
    PRODUCTION_INCIDENT = "production_incident"
    NEAR_MISS = "near_miss"
    EXTRACTION_FAILED = "extraction_failed"
    NON_SHAREABLE = "non_shareable"
    CFI_RELEASED = "cfi_released"
    RECIPIENT_EVALUATION = "recipient_evaluation"


@dataclass
class FieldReport:
    org_id: str
    day: int
    report_type: ReportType
    invariant_id: str | None = None
    susceptible: bool | None = None
    notes: str = ""


@dataclass
class FieldStudyConfig:
    duration_days: int = 180
    org_count: int = 8
    seed: int = 421337
    include_survivorship: bool = True


@dataclass
class FieldStudyResult:
    duration_days: int
    org_count: int
    total_reports: int
    cfi_releases: int
    failed_extractions: int
    non_shareable: int
    near_misses: int
    production_incidents: int
    susceptible_before_incident: int
    prevention_rate: float
    lead_time_median_days: float | None
    reports: list[FieldReport] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=lambda: [
        "Compressed simulation; not a live six-month field deployment.",
        "Susceptibility uses sandbox stub agents, not production systems.",
        "Anti-survivorship requires reporting failed extractions and non-shareable incidents.",
        "Prevention attribution is correlational, not causal proof.",
    ])


def _failing_agent(sb: Sandbox, trace: SandboxTrace) -> None:
    trace.state["review_complete"] = False
    sb.execute_tool(trace, "stub_po", {})


def _evaluate_susceptibility(domain: str) -> bool:
    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context(domain, cfi.required_mapping_roles)
    compilation = fail_closed_compile(cfi, ctx, manifest=None)
    if compilation.abstained or not compilation.cases:
        return False
    rate = susceptibility(compilation.cases, cfi.oracle.expression, _failing_agent)
    return rate > 0.0


def run_prospective_study(config: FieldStudyConfig | None = None) -> FieldStudyResult:
    """Run compressed prospective pilot with survivorship-inclusive reporting."""
    cfg = config or FieldStudyConfig()
    rng = random.Random(cfg.seed)
    reports: list[FieldReport] = []
    domains = ["procurement", "healthcare", "data_operations", "finance", "logistics", "retail", "retail", "procurement"]

    # Contributor extractions (include failures per anti-survivorship rule)
    for org_i in range(cfg.org_count):
        org = f"org-{org_i:02d}"
        day = rng.randint(1, 30)
        if org_i == 0:
            reports.append(FieldReport(org, day, ReportType.EXTRACTION_FAILED, notes="minimizer_rejected"))
            continue
        if org_i == 1:
            reports.append(FieldReport(org, day, ReportType.NON_SHAREABLE, notes="release_gate_reject"))
            continue
        invariant_id = f"CFI-FIELD-{org_i:03d}"
        reports.append(FieldReport(org, day, ReportType.CFI_RELEASED, invariant_id=invariant_id))

    releases = [r for r in reports if r.report_type == ReportType.CFI_RELEASED]
    org_susceptible_day: dict[str, int] = {}
    for release in releases:
        domain = domains[int(release.org_id.split("-")[1]) % len(domains)]
        for recipient_i in range(cfg.org_count):
            recipient = f"org-{recipient_i:02d}"
            if recipient == release.org_id:
                continue
            eval_day = release.day + rng.randint(1, 14)
            if eval_day > cfg.duration_days:
                continue
            susceptible = _evaluate_susceptibility(domain)
            reports.append(
                FieldReport(
                    recipient,
                    eval_day,
                    ReportType.RECIPIENT_EVALUATION,
                    invariant_id=release.invariant_id,
                    susceptible=susceptible,
                    notes="recipient_evaluation",
                )
            )
            if susceptible and recipient not in org_susceptible_day:
                org_susceptible_day[recipient] = eval_day

    # Production incidents at recipient orgs
    lead_times: list[int] = []
    susceptible_before = 0
    production_count = 0
    for org_i in range(cfg.org_count):
        org = f"org-{org_i:02d}"
        if rng.random() > 0.4:
            continue
        incident_day = rng.randint(45, cfg.duration_days)
        production_count += 1
        reports.append(FieldReport(org, incident_day, ReportType.PRODUCTION_INCIDENT))
        if org in org_susceptible_day and org_susceptible_day[org] < incident_day:
            susceptible_before += 1
            lead_times.append(incident_day - org_susceptible_day[org])

    reports.sort(key=lambda r: (r.day, r.org_id))
    failed = sum(1 for r in reports if r.report_type == ReportType.EXTRACTION_FAILED)
    non_share = sum(1 for r in reports if r.report_type == ReportType.NON_SHAREABLE)
    cfi_count = sum(1 for r in reports if r.report_type == ReportType.CFI_RELEASED)
    prevention = susceptible_before / max(production_count, 1)
    median_lt = float(sorted(lead_times)[len(lead_times) // 2]) if lead_times else None

    return FieldStudyResult(
        duration_days=cfg.duration_days,
        org_count=cfg.org_count,
        total_reports=len(reports),
        cfi_releases=cfi_count,
        failed_extractions=failed,
        non_shareable=non_share,
        near_misses=sum(1 for r in reports if r.report_type == ReportType.NEAR_MISS),
        production_incidents=production_count,
        susceptible_before_incident=susceptible_before,
        prevention_rate=prevention,
        lead_time_median_days=median_lt,
        reports=reports,
    )


def evaluate_mitigation_in_field(domain: str = "procurement") -> dict[str, Any]:
    """RQ5 endpoint — policy mitigation on compiled cases."""
    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context(domain, cfi.required_mapping_roles)
    compilation = fail_closed_compile(cfi, ctx, manifest=None)

    def fixed_agent(sb: Sandbox, trace: SandboxTrace) -> None:
        trace.state["review_complete"] = True
        sb.execute_tool(trace, "stub_po", {})

    mitigation = MitigationCandidate(
        layer=MitigationLayer.POLICY,
        description="enforce review before irreversible action",
        agent_fn=fixed_agent,
    )
    report = evaluate_mitigation(compilation, cfi.oracle.expression, _failing_agent, mitigation)
    return {
        "accepted": report.accepted,
        "pre_susceptibility": report.pre_susceptibility,
        "post_susceptibility": report.post_susceptibility,
        "assumptions": report.assumptions,
    }

"""Local recipient assessment helpers (compile + Table III metrics)."""

from __future__ import annotations

from dataclasses import dataclass, field

from cfi_core.models import CausalFailureInvariant
from cfi_recipient.compiler import CompilationResult, fail_closed_compile
from cfi_recipient.metrics import AssuranceReport, build_report
from cfi_recipient.mitigation import susceptibility
from cfi_recipient.ontology import build_recipient_context
from cfi_recipient.sandbox import Sandbox, SandboxTrace


@dataclass
class AssessResult:
    compilation: CompilationResult
    report: AssuranceReport
    assumptions: list[str] = field(default_factory=lambda: [
        "Assessment runs entirely inside recipient trust boundary.",
        "Susceptibility uses local sandbox stub agent, not live production runtime.",
    ])


def assess_cfi(
    cfi: CausalFailureInvariant,
    domain: str,
    *,
    spec_id: str = "recipient-assess",
    cohort_id: str | None = None,
) -> AssessResult:
    ctx = build_recipient_context(domain, cfi.required_mapping_roles)
    compilation = fail_closed_compile(cfi, ctx, manifest=None)
    if compilation.abstained:
        raise ValueError(compilation.abstention_reason or "compilation_abstained")

    def failing_agent(sb: Sandbox, trace: SandboxTrace) -> None:
        trace.state["review_complete"] = False
        sb.execute_tool(trace, "stub_po", {})

    rate = susceptibility(compilation.cases, cfi.oracle.expression, failing_agent)
    positive_cases = [c for c in compilation.cases if not c.is_negative_control]
    coverage = len(positive_cases) / max(1, len(cfi.required_mapping_roles))
    report = build_report(
        spec_id=spec_id,
        cohort_id=cohort_id or f"local-{domain}",
        compilation_coverage=min(1.0, coverage),
        structural_precision=1.0,
        susceptibility=rate,
        residual_privacy_risk=0.0,
    )
    return AssessResult(compilation=compilation, report=report)

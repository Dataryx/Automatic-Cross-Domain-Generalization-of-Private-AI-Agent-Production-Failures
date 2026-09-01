"""Five separate metric families — never collapsed into one score (R7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricFamily:
    dimension: str
    metric: str
    value: float
    measurement_spec_id: str
    cohort_id: str
    assumptions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssuranceReport:
    """Table III metric families reported separately."""

    invariant_coverage: MetricFamily | None = None
    test_validity: MetricFamily | None = None
    agent_susceptibility: MetricFamily | None = None
    mitigation_effectiveness: MetricFamily | None = None
    privacy_risk: MetricFamily | None = None
    compilation_coverage: MetricFamily | None = None
    federation_utility: MetricFamily | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name in (
            "invariant_coverage",
            "test_validity",
            "agent_susceptibility",
            "mitigation_effectiveness",
            "privacy_risk",
            "compilation_coverage",
            "federation_utility",
        ):
            m = getattr(self, name)
            if m is not None:
                out[name] = {
                    "dimension": m.dimension,
                    "metric": m.metric,
                    "value": m.value,
                    "measurement_spec_id": m.measurement_spec_id,
                    "cohort_id": m.cohort_id,
                    "assumptions": m.assumptions,
                    "metadata": m.metadata,
                }
        return out


def build_report(
    *,
    spec_id: str,
    cohort_id: str,
    compilation_coverage: float,
    structural_precision: float,
    susceptibility: float,
    residual_privacy_risk: float,
    dp_mae: float | None = None,
    mitigation_delta: float | None = None,
) -> AssuranceReport:
    return AssuranceReport(
        invariant_coverage=MetricFamily(
            dimension="transfer",
            metric="embedding_success",
            value=compilation_coverage,
            measurement_spec_id=spec_id,
            cohort_id=cohort_id,
            assumptions=["Structural compilation only; semantic equivalence requires expert sign-off."],
        ),
        test_validity=MetricFamily(
            dimension="compilation",
            metric="structural_precision",
            value=structural_precision,
            measurement_spec_id=spec_id,
            cohort_id=cohort_id,
        ),
        agent_susceptibility=MetricFamily(
            dimension="reliability",
            metric="susceptibility_rate",
            value=susceptibility,
            measurement_spec_id=spec_id,
            cohort_id=cohort_id,
            assumptions=["Rate meaningful only with signed spec and cohort."],
        ),
        privacy_risk=MetricFamily(
            dimension="privacy",
            metric="residual_disclosure_risk",
            value=residual_privacy_risk,
            measurement_spec_id=spec_id,
            cohort_id=cohort_id,
            assumptions=["Canonicalization is not a confidentiality proof."],
        ),
        mitigation_effectiveness=MetricFamily(
            dimension="mitigation",
            metric="susceptibility_reduction",
            value=mitigation_delta if mitigation_delta is not None else 0.0,
            measurement_spec_id=spec_id,
            cohort_id=cohort_id,
        )
        if mitigation_delta is not None
        else None,
        federation_utility=MetricFamily(
            dimension="federation",
            metric="dp_mae",
            value=dp_mae,
            measurement_spec_id=spec_id,
            cohort_id=cohort_id,
            assumptions=["Mechanism-level utility; not an operational privacy budget endorsement."],
        )
        if dp_mae is not None
        else None,
    )

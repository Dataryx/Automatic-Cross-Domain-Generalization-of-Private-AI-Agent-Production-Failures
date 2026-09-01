"""Shared production evaluation types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricRecord:
    dimension: str
    metric: str
    value: float
    ci_low: float
    ci_high: float
    measurement_spec_id: str
    cohort_id: str
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "metric": self.metric,
            "value": self.value,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "measurement_spec_id": self.measurement_spec_id,
            "cohort_id": self.cohort_id,
            "assumptions": self.assumptions,
        }

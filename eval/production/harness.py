"""Preregistered production evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import json

from cfi_core.signing import KeyPair, Signer


class ResearchQuestion(str, Enum):
    RQ1_CAUSAL_VALIDITY = "rq1_causal_validity"
    RQ2_CROSS_DOMAIN = "rq2_cross_domain"
    RQ3_DISCOVERY = "rq3_discovery"
    RQ4_PRIVACY = "rq4_privacy"
    RQ5_MITIGATION = "rq5_mitigation"
    RQ6_NETWORK_UTILITY = "rq6_network_utility"


BASELINES = [
    "raw_incident_replay",
    "pii_redacted_narrative",
    "taxonomy_label_guidance",
    "local_incident_regression",
    "policy_only_generation",
    "llm_paraphrase",
    "embedding_retrieval",
    "manual_metamorphic",
    "cfi_no_minimization",
    "cfi_no_canonicalization",
    "cfi_no_negative_controls",
    "centralized_pooled_upper_bound",
]


@dataclass
class Preregistration:
    study_id: str
    primary_endpoint: str
    research_questions: list[ResearchQuestion]
    baselines: list[str]
    privacy_thresholds: dict[str, float]
    signed_commitment: str | None = None


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


def seal_preregistration(prereg: Preregistration, key: KeyPair) -> Preregistration:
    payload = {
        "study_id": prereg.study_id,
        "primary_endpoint": prereg.primary_endpoint,
        "privacy_thresholds": prereg.privacy_thresholds,
    }
    sig, _ = Signer(key).sign_package(payload)
    prereg.signed_commitment = sig
    return prereg


def run_baseline(name: str, config: dict[str, Any]) -> MetricRecord:
    """Stub runner — each baseline returns structured metrics with spec binding."""
    return MetricRecord(
        dimension="compilation",
        metric="coverage",
        value=0.0 if name == "llm_paraphrase" else 1.0,
        ci_low=0.0,
        ci_high=1.0,
        measurement_spec_id=config.get("spec_id", "unset"),
        cohort_id=config.get("cohort_id", "unset"),
        assumptions=["Production evaluation requires live data collection."],
    )


def main(output_dir: str = "eval/production/output") -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    key = KeyPair.generate("research-lead")
    prereg = seal_preregistration(
        Preregistration(
            study_id="cfi-fed-prod-001",
            primary_endpoint="rq3_unique_failure_yield",
            research_questions=list(ResearchQuestion),
            baselines=BASELINES,
            privacy_thresholds={"source_attribution": 0.3, "reconstruction": 0.3},
        ),
        key,
    )
    (out / "preregistration.json").write_text(
        json.dumps(
            {
                "study_id": prereg.study_id,
                "signed_commitment": prereg.signed_commitment,
                "baselines": prereg.baselines,
            },
            indent=2,
        )
    )
    results = [run_baseline(b, {"spec_id": "prod-spec-1", "cohort_id": "cohort-1"}).__dict__ for b in BASELINES]
    (out / "baseline_stubs.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

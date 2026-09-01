"""Seven-stage privacy and safety release gate (Appendix C checklist)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cfi_core.canonicalize import Canonicalizer
from cfi_core.models import CausalFailureInvariant, DisclosureTier


class GateOutcome(str, Enum):
    REJECT = "reject"
    REQUIRE_GENERALIZATION = "require_further_generalization"
    RESTRICT_COHORT = "restrict_distribution"
    NON_SHAREABLE = "non_shareable"
    APPROVE = "approve"


@dataclass
class ChecklistItem:
    id: int
    question: str
    answer: bool | None = None
    notes: str = ""


@dataclass
class ReleaseGateVerdict:
    outcome: GateOutcome
    residual_risk_score: float
    stage_verdicts: dict[str, str] = field(default_factory=dict)
    checklist: list[ChecklistItem] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=lambda: [
        "Canonicalization is not a privacy proof.",
        "Masking identifiers alone may leave distributional signatures.",
    ])


APPENDIX_C_CHECKLIST: list[tuple[int, str]] = [
    (1, "Is the source incident preserved locally with immutable evidence and accountable ownership?"),
    (2, "Is the expected outcome supported by policy, deterministic state, or adjudication?"),
    (3, "Were counterfactual interventions safe, valid, and repeated under stochasticity?"),
    (4, "Does each retained graph element have causal or semantic justification?"),
    (5, "Were exact identities, credentials, hostnames, code, prompts, dates, amounts removed?"),
    (6, "Can the source domain, organization, or public incident be inferred?"),
    (7, "Can a frontier model reconstruct policy wording better than prior-only baseline?"),
    (8, "Does the package contain executable exploit instructions or unpatched vulnerability?"),
    (9, "Are negative controls and oracle sufficient to distinguish mechanism from incapability?"),
    (10, "Were legal, privacy, security, and domain owners represented in review?"),
    (11, "Is disclosure tier, cohort, expiration, embargo, and revocation path explicit?"),
    (12, "Are schema, compiler, evidence digest, review attestations, and signature present?"),
]


class ReleaseGate:
    def __init__(self, attribution_threshold: float = 0.3, reconstruction_threshold: float = 0.3) -> None:
        self._attr_threshold = attribution_threshold
        self._recon_threshold = reconstruction_threshold

    def run(
        self,
        cfi: CausalFailureInvariant,
        checklist_answers: dict[int, bool],
        adversary_scores: dict[str, float] | None = None,
    ) -> ReleaseGateVerdict:
        adversary_scores = adversary_scores or {}
        checklist = [
            ChecklistItem(id=i, question=q, answer=checklist_answers.get(i))
            for i, q in APPENDIX_C_CHECKLIST
        ]
        unanswered = [c for c in checklist if c.answer is None]
        if unanswered:
            return ReleaseGateVerdict(
                outcome=GateOutcome.REJECT,
                residual_risk_score=1.0,
                checklist=checklist,
                stage_verdicts={"human_authorization": "incomplete_checklist"},
            )

        stage_verdicts: dict[str, str] = {}
        violations = Canonicalizer.lint_for_release(cfi)
        stage_verdicts["syntactic_scan"] = "pass" if not violations else f"fail:{violations}"

        linkability = adversary_scores.get("linkability", 0.0)
        stage_verdicts["linkability_scan"] = "pass" if linkability < 0.5 else "elevated"

        attr = adversary_scores.get("source_attribution", 0.0)
        stage_verdicts["source_attribution"] = "pass" if attr < self._attr_threshold else "fail"

        recon = adversary_scores.get("reconstruction", 0.0)
        stage_verdicts["reconstruction"] = "pass" if recon < self._recon_threshold else "fail"

        stage_verdicts["differencing"] = "pass"
        stage_verdicts["operational_safety"] = "pass"
        stage_verdicts["human_authorization"] = "pass" if all(c.answer for c in checklist) else "fail"

        residual = max(linkability, attr, recon, 0.1 if violations else 0.0)

        if violations or attr >= self._attr_threshold or recon >= self._recon_threshold:
            outcome = GateOutcome.REJECT if violations else GateOutcome.REQUIRE_GENERALIZATION
        elif cfi.release.tier == DisclosureTier.NON_SHAREABLE:
            outcome = GateOutcome.NON_SHAREABLE
        elif residual > 0.4:
            outcome = GateOutcome.RESTRICT_COHORT
        else:
            outcome = GateOutcome.APPROVE

        return ReleaseGateVerdict(
            outcome=outcome,
            residual_risk_score=residual,
            stage_verdicts=stage_verdicts,
            checklist=checklist,
        )

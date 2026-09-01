"""Consortium coordinator — Phase 5 multi-tenant aggregation with anti-Sybil controls."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cfi_core.wire import CohortManifest
from cfi_federation import ClippedContribution, secure_aggregate
from cfi_federation.accountant import PrivacyAccountant
from cfi_federation.protocol import recipient_evaluate_and_contribute


class ParticipationStatus(str, Enum):
    ELIGIBLE = "eligible"
    DROPPED = "dropped"
    REJECTED_SYBIL = "rejected_sybil"
    REJECTED_VERSION = "rejected_version"
    REJECTED_OUTLIER = "rejected_outlier"


@dataclass
class TenantIdentity:
    tenant_id: str
    org_family: str
    verified: bool = True
    compiler_version: str = "0.1.0"


@dataclass
class TenantSubmission:
    identity: TenantIdentity
    contribution: ClippedContribution | None = None
    envelope: dict[str, Any] | None = None
    status: ParticipationStatus = ParticipationStatus.ELIGIBLE
    reason: str = ""


@dataclass
class ConsortiumConfig:
    minimum_k: int = 10
    max_per_org_family: int = 2
    dropout_rate: float = 0.1
    required_compiler_version: str = "0.1.0"
    outlier_failure_cap: int = 50
    total_epsilon_budget: float = 10.0


@dataclass
class ConsortiumRoundResult:
    released: bool
    noisy_prevalence: float | None
    participants: int
    rejected: list[TenantSubmission] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=lambda: [
        "Aggregate prevalence is cohort- and specification-dependent.",
        "DP protects tenant influence; not poorly generalized CFIs.",
        "Secure aggregation assumes fewer than threshold servers collude.",
    ])
    accountant_remaining: float | None = None
    reason: str = ""


class ConsortiumCoordinator:
    """§5.16 eligibility, thresholds, and anti-Sybil controls."""

    def __init__(self, config: ConsortiumConfig | None = None) -> None:
        self._config = config or ConsortiumConfig()
        self._accountant = PrivacyAccountant(total_epsilon=self._config.total_epsilon_budget)

    def admit_tenants(self, identities: list[TenantIdentity]) -> list[TenantSubmission]:
        family_counts: dict[str, int] = {}
        submissions: list[TenantSubmission] = []
        for ident in identities:
            sub = TenantSubmission(identity=ident)
            if not ident.verified:
                sub.status = ParticipationStatus.REJECTED_SYBIL
                sub.reason = "unverified_identity"
            elif ident.compiler_version != self._config.required_compiler_version:
                sub.status = ParticipationStatus.REJECTED_VERSION
                sub.reason = "compiler_version_mismatch"
            else:
                count = family_counts.get(ident.org_family, 0)
                if count >= self._config.max_per_org_family:
                    sub.status = ParticipationStatus.REJECTED_SYBIL
                    sub.reason = "org_family_cap_exceeded"
                else:
                    family_counts[ident.org_family] = count + 1
            submissions.append(sub)
        return submissions

    def simulate_dropout(self, submissions: list[TenantSubmission], rng: random.Random) -> None:
        for sub in submissions:
            if sub.status != ParticipationStatus.ELIGIBLE:
                continue
            if rng.random() < self._config.dropout_rate:
                sub.status = ParticipationStatus.DROPPED
                sub.reason = "dropout"

    def collect_contributions(
        self,
        cfi_package: dict[str, Any],
        manifest: CohortManifest,
        submissions: list[TenantSubmission],
        roles: list[str],
        domains: list[str],
    ) -> list[ClippedContribution]:
        contributions: list[ClippedContribution] = []
        eligible = [s for s in submissions if s.status == ParticipationStatus.ELIGIBLE]
        for i, sub in enumerate(eligible):
            domain = domains[i % len(domains)]
            try:
                contrib, envelope, _ = recipient_evaluate_and_contribute(
                    cfi_package, domain, sub.identity.tenant_id, manifest, roles
                )
            except ValueError as exc:
                sub.status = ParticipationStatus.DROPPED
                sub.reason = str(exc)
                continue
            if contrib.failures > self._config.outlier_failure_cap:
                sub.status = ParticipationStatus.REJECTED_OUTLIER
                sub.reason = "poisoning_outlier"
                continue
            sub.contribution = contrib
            sub.envelope = envelope
            contributions.append(contrib)
        return contributions

    def run_round(
        self,
        cfi_package: dict[str, Any],
        manifest: CohortManifest,
        identities: list[TenantIdentity],
        roles: list[str],
        domains: list[str],
        seed: int = 421337,
    ) -> ConsortiumRoundResult:
        rng = random.Random(seed)
        submissions = self.admit_tenants(identities)
        self.simulate_dropout(submissions, rng)
        contributions = self.collect_contributions(
            cfi_package, manifest, submissions, roles, domains
        )

        rejected = [s for s in submissions if s.status != ParticipationStatus.ELIGIBLE or s.contribution is None]
        if len(contributions) < self._config.minimum_k:
            return ConsortiumRoundResult(
                released=False,
                noisy_prevalence=None,
                participants=len(contributions),
                rejected=rejected,
                reason="below_minimum_k",
            )

        verdict = self._accountant.request_release(
            manifest.privacy_budget_epsilon,
            len(contributions),
            manifest.aggregation_epoch,
            manifest.measurement_spec.spec_id,
        )
        if not verdict.allowed:
            return ConsortiumRoundResult(
                released=False,
                noisy_prevalence=None,
                participants=len(contributions),
                rejected=rejected,
                accountant_remaining=verdict.remaining_epsilon,
                reason=verdict.reason,
            )

        release = secure_aggregate(
            contributions,
            [],
            threshold=2,
            minimum_k=self._config.minimum_k,
            epsilon=manifest.privacy_budget_epsilon,
            measurement_spec_id=manifest.measurement_spec.spec_id,
            rng=rng,
        )
        if release is None:
            return ConsortiumRoundResult(
                released=False,
                noisy_prevalence=None,
                participants=len(contributions),
                rejected=rejected,
                reason="aggregation_failed",
            )

        return ConsortiumRoundResult(
            released=True,
            noisy_prevalence=release.noisy_prevalence,
            participants=release.cohort_size,
            rejected=rejected,
            accountant_remaining=verdict.remaining_epsilon,
        )

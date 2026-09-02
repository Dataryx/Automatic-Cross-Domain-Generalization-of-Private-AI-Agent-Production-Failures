"""Recipient-side federation contribution helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cfi_core.wire import CohortManifest
from cfi_federation import ClippedContribution
from cfi_federation.protocol import recipient_evaluate_and_contribute


@dataclass
class FederationContribution:
    contribution: ClippedContribution
    share_envelope: dict[str, Any]
    raw_failures: int
    assumptions: list[str] = field(default_factory=lambda: [
        "Only clipped secret shares and clipped counts may egress recipient boundary.",
        "Share envelope is a wire-format artifact; aggregation may use clipped counts directly.",
    ])


def contribute_from_package(
    cfi_package: dict[str, Any],
    *,
    domain: str,
    tenant_id: str,
    manifest: CohortManifest,
    roles: list[str],
) -> FederationContribution:
    contrib, envelope, failures = recipient_evaluate_and_contribute(
        cfi_package, domain, tenant_id, manifest, roles
    )
    return FederationContribution(
        contribution=contrib,
        share_envelope=envelope,
        raw_failures=failures,
    )

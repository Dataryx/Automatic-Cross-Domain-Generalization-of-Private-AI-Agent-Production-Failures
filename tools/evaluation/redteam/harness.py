"""Red-team harnesses for §7.2 adversaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AttackResult:
    adversary: str
    success_rate: float
    metric: str
    notes: str


def honest_but_curious_registry(cfi_packages: list[dict[str, Any]]) -> AttackResult:
    """Attempt source inference from stored CFIs."""
    domains_guessed = 0
    for pkg in cfi_packages:
        if "retail" in str(pkg).lower():
            domains_guessed += 1
    rate = domains_guessed / max(len(cfi_packages), 1)
    return AttackResult("honest_but_curious_registry", rate, "source_domain_inference", "")


def malicious_recipient_probe(cfi: dict[str, Any]) -> AttackResult:
    leaked = "prompt" in str(cfi).lower()
    return AttackResult("malicious_recipient", float(leaked), "schema_probe", "")


def malicious_contributor(cfi: dict[str, Any]) -> AttackResult:
    dangerous = "exploit" in str(cfi).lower() or "eval(" in str(cfi)
    return AttackResult("malicious_contributor", float(dangerous), "payload_scan", "")


def sybil_organizations(contributions: list[str], cap: int = 1) -> AttackResult:
    from collections import Counter

    counts = Counter(contributions)
    violation = any(v > cap for v in counts.values())
    return AttackResult("sybil_organizations", float(violation), "contribution_cap", "")


def collusion_reveal(shares: list[tuple[int, int]], threshold: int) -> AttackResult:
    from cfi_federation import shamir_recover

    try:
        if len(shares) >= threshold:
            shamir_recover(shares[:threshold])
            revealed = True
        else:
            revealed = False
    except Exception:
        revealed = False
    return AttackResult("collusion", float(revealed), "share_recovery", "")


def external_observer_timing(public_events: list[str], release_times: list[str]) -> AttackResult:
    correlated = len(set(public_events) & set(release_times)) > 0
    return AttackResult("external_observer", float(correlated), "timing_correlation", "")


def model_provider_traffic(tools_called: list[str], production_tools: list[str]) -> AttackResult:
    overlap = len(set(tools_called) & set(production_tools)) / max(len(tools_called), 1)
    return AttackResult("model_provider", overlap, "tool_overlap", "")


ADVERSARY_RUNNERS = [
    honest_but_curious_registry,
    malicious_recipient_probe,
    malicious_contributor,
    sybil_organizations,
    collusion_reveal,
    external_observer_timing,
    model_provider_traffic,
]

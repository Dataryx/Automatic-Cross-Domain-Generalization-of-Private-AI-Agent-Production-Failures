"""Release-gate adversary models for source attribution and reconstruction.

These are calibrated internal adversaries for the release gate — NOT privacy proofs.
"""

from __future__ import annotations

from dataclasses import dataclass

from cfi_contributor.adversary_features import DOMAIN_KEYWORDS, LITERAL_PATTERN, SECRET_PATTERN
from cfi_contributor.trained_adversary import TrainedAttributionModel
from cfi_core.canonicalize import Canonicalizer
from cfi_core.models import CausalFailureInvariant


@dataclass
class AdversaryReport:
    source_attribution: float
    reconstruction: float
    linkability: float
    notes: str = ""


class ReleaseGateAdversaries:
    """Heuristic adversaries aligned with §5.6 gate stages 2–4."""

    def __init__(self, use_trained_attribution: bool = True) -> None:
        self._trained = TrainedAttributionModel() if use_trained_attribution else None

    def score_cfi(self, cfi: CausalFailureInvariant, source_domain: str | None = None) -> AdversaryReport:
        searchable = " ".join([cfi.failure_predicate, cfi.oracle.expression, *cfi.controls])

        node_count = len(cfi.nodes)
        edge_count = len(cfi.edges)
        linkability = min(1.0, (node_count + edge_count) / 30.0)
        if any(n.extensions for n in cfi.nodes):
            linkability = min(1.0, linkability + 0.15)

        attr_hits = 0
        for keywords in DOMAIN_KEYWORDS.values():
            if any(kw in searchable.lower() for kw in keywords):
                attr_hits += 1
        source_attribution = attr_hits / max(len(DOMAIN_KEYWORDS), 1)
        if source_domain:
            source_attribution = max(source_attribution, 0.9)
        if self._trained is not None:
            trained = self._trained.score_cfi(cfi)
            source_attribution = max(source_attribution, trained.probability)

        recon = 0.0
        if SECRET_PATTERN.search(searchable):
            recon = 1.0
        elif LITERAL_PATTERN.search(searchable):
            recon = 0.6
        elif Canonicalizer.lint_for_release(cfi):
            recon = 0.5

        return AdversaryReport(
            source_attribution=source_attribution,
            reconstruction=recon,
            linkability=linkability,
            notes="Heuristic adversary; not a privacy guarantee.",
        )

    def score_raw_trace(self, narrative: str) -> AdversaryReport:
        attr = 0.0
        for keywords in DOMAIN_KEYWORDS.values():
            if any(kw in narrative.lower() for kw in keywords):
                attr = max(attr, 0.95)
        token_leak = 1.0 if LITERAL_PATTERN.search(narrative) else 0.0
        return AdversaryReport(
            source_attribution=attr,
            reconstruction=token_leak,
            linkability=0.8,
            notes="Raw trace baseline.",
        )

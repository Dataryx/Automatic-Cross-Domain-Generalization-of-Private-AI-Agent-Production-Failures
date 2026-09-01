"""Release-gate adversary models for source attribution and reconstruction.

These are calibrated internal adversaries for the release gate — NOT privacy proofs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from cfi_core.canonicalize import Canonicalizer
from cfi_core.models import CausalFailureInvariant


@dataclass
class AdversaryReport:
    source_attribution: float
    reconstruction: float
    linkability: float
    notes: str = ""


DOMAIN_KEYWORDS = {
    "retail": {"order", "sku", "checkout", "cart"},
    "procurement": {"vendor", "requisition", "po", "sourcing"},
    "healthcare": {"patient", "coverage", "claim", "procedure"},
    "finance": {"ledger", "wire", "account", "settlement"},
    "data_operations": {"pipeline", "dataset", "schema", "partition"},
}

SECRET_PATTERN = re.compile(r"(api[_-]?key|password|secret|sk-[a-zA-Z0-9]{20,})", re.I)
LITERAL_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\$\d+")


class ReleaseGateAdversaries:
    """Heuristic adversaries aligned with §5.6 gate stages 2–4."""

    def score_cfi(self, cfi: CausalFailureInvariant, source_domain: str | None = None) -> AdversaryReport:
        blob = cfi.model_dump_json()
        searchable = " ".join([cfi.failure_predicate, cfi.oracle.expression, *cfi.controls])

        # Linkability: rare topology / uncommon extensions
        node_count = len(cfi.nodes)
        edge_count = len(cfi.edges)
        linkability = min(1.0, (node_count + edge_count) / 30.0)
        if any(n.extensions for n in cfi.nodes):
            linkability = min(1.0, linkability + 0.15)

        # Source attribution via domain keyword overlap (canonical CFI should be low)
        attr_hits = 0
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in searchable.lower() for kw in keywords):
                attr_hits += 1
        source_attribution = attr_hits / max(len(DOMAIN_KEYWORDS), 1)
        if source_domain:
            source_attribution = max(source_attribution, 0.9)

        # Reconstruction: secrets, literals, domain nouns in predicate fields
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
        """Baseline for comparison — raw traces leak easily."""
        attr = 0.0
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in narrative.lower() for kw in keywords):
                attr = max(attr, 0.95)
        token_leak = 1.0 if LITERAL_PATTERN.search(narrative) else 0.0
        return AdversaryReport(
            source_attribution=attr,
            reconstruction=token_leak,
            linkability=0.8,
            notes="Raw trace baseline.",
        )

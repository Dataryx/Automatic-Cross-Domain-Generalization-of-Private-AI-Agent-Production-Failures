"""Five-stage canonicalization pipeline.

IMPORTANT: Canonicalization is NOT a privacy proof. It reduces accidental disclosure
and enables interoperability but does not establish confidentiality guarantees.
Every report citing canonicalization must state this limitation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from cfi_core.jcs import canonicalize, digest_hex
from cfi_core.models import CausalFailureInvariant, CFINode, CFIEdge, NodeType


APPROVED_VALUE_CLASSES = {
    "above_threshold",
    "below_threshold",
    "stale_after_update",
    "exception_active",
    "irreversible_external",
    "amount_above_approval_threshold",
}

DOMAIN_NOUN_PATTERN = re.compile(
    r"\b(refund|customer|patient|invoice|purchase|retail|healthcare|vendor|supplier)\b",
    re.I,
)
SECRET_PATTERN = re.compile(
    r"(api[_-]?key|password|secret|bearer\s+\S+|sk-[a-zA-Z0-9]{20,})",
    re.I,
)
EXACT_LITERAL_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\$\d+|\b[A-Z]{2,}-\d+\b")


@dataclass
class CanonicalizationReport:
    stages_completed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked_literals: list[str] = field(default_factory=list)
    dedup_digest: str | None = None


class Canonicalizer:
    """Ordered five-stage canonicalization."""

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed
        self._role_counter: dict[str, int] = {}

    def _allocate_role(self, node_type: str) -> str:
        key = node_type.lower()
        idx = self._role_counter.get(key, 0)
        self._role_counter[key] = idx + 1
        return f"{key}_{idx}"

    def alpha_rename(self, cfi: CausalFailureInvariant) -> CausalFailureInvariant:
        id_map: dict[str, str] = {}
        new_nodes: list[CFINode] = []
        for node in cfi.nodes:
            new_id = self._allocate_role(node.type.value)
            id_map[node.id] = new_id
            role = node.role or new_id
            new_nodes.append(
                CFINode(
                    id=new_id,
                    type=node.type,
                    role=role,
                    value_class=node.value_class,
                    risk=node.risk,
                    extensions=node.extensions,
                )
            )
        new_edges = [
            CFIEdge(
                source=id_map[e.source],
                edge_type=e.edge_type,
                target=id_map[e.target],
                status=e.status,
                provenance=e.provenance,
                confidence=e.confidence,
                explanation=e.explanation,
                reviewer_id=e.reviewer_id,
            )
            for e in cfi.edges
        ]
        return cfi.model_copy(update={"nodes": new_nodes, "edges": new_edges})

    def literal_bucket_scan(self, cfi: CausalFailureInvariant) -> list[str]:
        blocked: list[str] = []
        text_fields = [cfi.failure_predicate, cfi.oracle.expression, *[c.controls]]
        for text in text_fields:
            for match in EXACT_LITERAL_PATTERN.findall(text):
                blocked.append(match)
        return blocked

    def vocabulary_project(self, cfi: CausalFailureInvariant) -> CausalFailureInvariant:
        # Roles already abstract; strip any domain nouns from extensions
        clean_nodes = []
        for node in cfi.nodes:
            ext = {k: v for k, v in node.extensions.items() if not DOMAIN_NOUN_PATTERN.search(str(v))}
            clean_nodes.append(node.model_copy(update={"extensions": ext}))
        return cfi.model_copy(update={"nodes": clean_nodes})

    def graph_normalize(self, cfi: CausalFailureInvariant) -> bytes:
        data = cfi.model_dump(mode="json", exclude={"signature", "certificate_chain"})
        data["nodes"] = sorted(data["nodes"], key=lambda n: (n["type"], n.get("role", ""), n["id"]))
        data["edges"] = sorted(
            data["edges"],
            key=lambda e: (e["source"], e["edge_type"], e["target"]),
        )
        return canonicalize(data)

    def semantic_dedup_digest(self, canonical_bytes: bytes) -> str:
        import hashlib

        return hashlib.sha256(canonical_bytes).hexdigest()

    def canonicalize(self, cfi: CausalFailureInvariant) -> tuple[CausalFailureInvariant, CanonicalizationReport]:
        report = CanonicalizationReport()
        report.stages_completed.append("alpha_renaming")
        c1 = self.alpha_rename(cfi)

        blocked = self.literal_bucket_scan(c1)
        report.blocked_literals = blocked
        if blocked:
            report.warnings.append("Unknown or exact literals detected; release may be blocked")
        report.stages_completed.append("literal_bucketing")

        c2 = self.vocabulary_project(c1)
        report.stages_completed.append("vocabulary_projection")

        canonical_bytes = self.graph_normalize(c2)
        report.stages_completed.append("graph_normalization")

        report.dedup_digest = self.semantic_dedup_digest(canonical_bytes)
        report.stages_completed.append("semantic_deduplication")

        return c2, report

    @staticmethod
    def lint_for_release(cfi: CausalFailureInvariant) -> list[str]:
        """Hard linter: prohibited content checks."""
        violations: list[str] = []
        blob = cfi.model_dump_json()
        if DOMAIN_NOUN_PATTERN.search(blob):
            violations.append("domain_nouns_detected")
        if SECRET_PATTERN.search(blob):
            violations.append("secrets_detected")
        if EXACT_LITERAL_PATTERN.search(blob):
            violations.append("exact_literals_detected")
        for node in cfi.nodes:
            if node.type == NodeType.OUTCOME and node.role and "refund" in node.role.lower():
                violations.append("outcome_role_leakage")
        return violations

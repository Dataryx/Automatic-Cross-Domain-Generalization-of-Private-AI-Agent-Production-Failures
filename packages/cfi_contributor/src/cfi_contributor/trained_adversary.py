"""Lightweight sklearn attribution model — NOT a privacy proof."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression

from cfi_contributor.adversary_features import DOMAIN_KEYWORDS, LITERAL_PATTERN, SECRET_PATTERN
from cfi_core.models import CausalFailureInvariant


@dataclass
class TrainedAttributionScore:
    probability: float
    model: str = "logistic_regression_v1"
    notes: str = "Calibrated on synthetic domain-keyword features; not a privacy guarantee."


def _feature_vector(text: str, node_count: int, edge_count: int) -> list[float]:
    lower = text.lower()
    domain_hits = sum(1 for kws in DOMAIN_KEYWORDS.values() if any(kw in lower for kw in kws))
    return [
        float(domain_hits),
        float(node_count),
        float(edge_count),
        1.0 if LITERAL_PATTERN.search(text) else 0.0,
        1.0 if SECRET_PATTERN.search(text) else 0.0,
        float(len(text.split())),
    ]


class TrainedAttributionModel:
    """Synthetic-trained baseline adversary for release-gate calibration."""

    def __init__(self) -> None:
        self._model = LogisticRegression(max_iter=500)
        self._fit_default()

    def _fit_default(self) -> None:
        x_rows: list[list[float]] = []
        y: list[int] = []
        # Negative: domain-neutral canonical phrasing
        neutral_texts = [
            "exception_true AND action_committed AND NOT review_complete",
            "policy_violation when review missing before irreversible action",
            "general_permission overridden without verification",
        ]
        for text in neutral_texts:
            x_rows.append(_feature_vector(text, 7, 7))
            y.append(0)
        # Positive: domain-leaky narratives
        leaky_texts = [
            "retail checkout sku cart order failed at po release",
            "patient claim procedure coverage denied vendor requisition",
            "pipeline dataset schema partition publish without approval",
            "wire transfer ledger account settlement bypass review",
            "retail order sku checkout cart vendor po patient claim pipeline",
            "checkout cart sku order patient procedure vendor requisition wire ledger",
        ]
        for text in leaky_texts:
            x_rows.append(_feature_vector(text, 12, 10))
            y.append(1)
        self._model.fit(np.array(x_rows), np.array(y))

    def score_cfi(self, cfi: CausalFailureInvariant) -> TrainedAttributionScore:
        searchable = " ".join([cfi.failure_predicate, cfi.oracle.expression, *cfi.controls])
        features = _feature_vector(searchable, len(cfi.nodes), len(cfi.edges))
        prob = float(self._model.predict_proba(np.array([features]))[0][1])
        return TrainedAttributionScore(probability=prob)

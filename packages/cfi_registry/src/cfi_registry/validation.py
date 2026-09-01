"""Shared registry validation logic."""

from __future__ import annotations

from typing import Any

from cfi_core.models import CausalFailureInvariant
from cfi_core.signing import Verifier


def validate_and_parse_package(package: dict[str, Any]) -> CausalFailureInvariant:
    verifier = Verifier()
    if not verifier.verify(package):
        raise ValueError("Invalid signature")
    if "prompt" in str(package).lower() or "api_key" in str(package).lower():
        raise ValueError("Adversarial content rejected")
    try:
        return CausalFailureInvariant.model_validate(package)
    except Exception as exc:
        raise ValueError(f"Schema validation failed: {exc}") from exc

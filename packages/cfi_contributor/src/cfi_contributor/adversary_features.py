"""Shared adversary feature constants."""

from __future__ import annotations

import re

DOMAIN_KEYWORDS = {
    "retail": {"order", "sku", "checkout", "cart"},
    "procurement": {"vendor", "requisition", "po", "sourcing"},
    "healthcare": {"patient", "coverage", "claim", "procedure"},
    "finance": {"ledger", "wire", "account", "settlement"},
    "data_operations": {"pipeline", "dataset", "schema", "partition"},
}

SECRET_PATTERN = re.compile(r"(api[_-]?key|password|secret|sk-[a-zA-Z0-9]{20,})", re.I)
LITERAL_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\$\d+")

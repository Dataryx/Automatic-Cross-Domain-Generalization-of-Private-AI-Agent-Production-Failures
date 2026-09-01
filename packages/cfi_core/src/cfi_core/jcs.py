"""RFC 8785 JSON Canonicalization Scheme implementation.

Byte-stable canonical serialization for signing. Platform-independent when using
the same JSON structure.
"""

from __future__ import annotations

import json
from typing import Any


def _canonicalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _canonicalize_value(value[k]) for k in sorted(value.keys())}
    if isinstance(value, list):
        return [_canonicalize_value(v) for v in value]
    if isinstance(value, float):
        if value == 0.0 and str(value).startswith("-"):
            return 0.0
        # Use repr-like minimal form
        return float(format(value, ".15g"))
    return value


def canonicalize(obj: dict[str, Any] | list[Any]) -> bytes:
    """Return JCS-canonical UTF-8 bytes for signing."""
    normalized = _canonicalize_value(obj)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def digest_hex(obj: dict[str, Any]) -> str:
    import hashlib

    return hashlib.sha256(canonicalize(obj)).hexdigest()

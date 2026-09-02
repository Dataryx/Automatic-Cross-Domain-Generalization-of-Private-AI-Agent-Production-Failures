"""Append-only hash chain for local audit sink files (tamper-evidence prototype)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


GENESIS_HASH = "0" * 64


def worm_chain_hash(previous_hash: str, canonical_line: str) -> str:
    return hashlib.sha256(f"{previous_hash}:{canonical_line}".encode("utf-8")).hexdigest()


def read_worm_chain_head(file_path: Path) -> str:
    if not file_path.exists():
        return GENESIS_HASH
    last_line = ""
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                last_line = stripped
    if not last_line:
        return GENESIS_HASH
    record = json.loads(last_line)
    return str(record.get("chain_hash", GENESIS_HASH))


def wrap_worm_record(payload: dict[str, Any], *, previous_hash: str) -> dict[str, Any]:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    chain_hash = worm_chain_hash(previous_hash, canonical)
    return {
        "chain_prev": previous_hash,
        "chain_hash": chain_hash,
        "payload": payload,
    }

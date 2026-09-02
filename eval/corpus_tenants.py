"""Materialize multi-tenant private corpus layouts from benchmark bundles."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast


def materialize_tenant_corpus(
    source_bundles: Path,
    output_root: Path,
    *,
    tenant_count: int = 5,
    clean: bool = False,
) -> Path:
    """Copy benchmark bundles into per-tenant subdirs with unique incident ids."""
    if clean and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    bundle_paths = sorted(source_bundles.glob("*.json"))
    if not bundle_paths:
        raise FileNotFoundError(f"No bundles in {source_bundles}")

    for tenant_idx in range(tenant_count):
        tenant_id = f"tenant-{tenant_idx:02d}"
        tenant_dir = output_root / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        for bundle_path in bundle_paths:
            payload = cast(dict[str, Any], json.loads(bundle_path.read_text(encoding="utf-8")))
            stem = bundle_path.stem
            incident_id = f"{tenant_id}-{stem}"
            payload["incident_id"] = incident_id
            payload["evidence_store_ref"] = f"local://corpus/{tenant_id}/{incident_id}"
            metadata = dict(payload.get("metadata", {}))
            metadata["tenant_id"] = tenant_id
            payload["metadata"] = metadata
            out_path = tenant_dir / f"{incident_id}.json"
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return output_root

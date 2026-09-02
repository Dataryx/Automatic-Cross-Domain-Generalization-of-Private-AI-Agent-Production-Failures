"""Publish extracted corpus CFIs to a remote registry (signed packages only)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cfi_registry.client import RegistryClient


@dataclass
class PublishRecord:
    cfi_id: str
    package_path: str
    registered: bool
    error: str | None = None


@dataclass
class PublishReport:
    records: list[PublishRecord] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=lambda: [
        "Only signed CFI packages are published; raw incident bundles never egress.",
        "Duplicate invariant ids are skipped with an error record.",
        "Multiple corpus bundles may collapse to the same structural CFI id in the prototype pipeline.",
    ])

    @property
    def registered_count(self) -> int:
        return sum(1 for r in self.records if r.registered)


def discover_packages(packages_dir: Path) -> list[Path]:
    return sorted(packages_dir.glob("*.json"))


def publish_packages(
    packages_dir: Path,
    client: RegistryClient,
) -> PublishReport:
    """Register signed CFI JSON files; skip duplicate invariant ids within the batch."""
    report = PublishReport()
    seen_ids: set[str] = set()
    for path in discover_packages(packages_dir):
        record = PublishRecord(cfi_id=path.stem, package_path=str(path), registered=False)
        try:
            package = json.loads(path.read_text(encoding="utf-8"))
            invariant_id = str(package.get("id", path.stem))
            record.cfi_id = invariant_id
            if invariant_id in seen_ids:
                record.error = "duplicate_invariant_id_skipped"
                report.records.append(record)
                continue
            result = client.register(package)
            record.cfi_id = result.get("invariant_id", invariant_id)
            record.registered = True
            seen_ids.add(invariant_id)
        except Exception as exc:
            record.error = str(exc)
        report.records.append(record)
    return report


def write_publish_manifest(report: PublishReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "registered": report.registered_count,
        "assumptions": report.assumptions,
        "records": [r.__dict__ for r in report.records],
    }
    path = output_dir / "publish_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path

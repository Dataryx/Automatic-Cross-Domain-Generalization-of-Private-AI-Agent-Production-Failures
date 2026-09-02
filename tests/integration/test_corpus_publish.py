"""Corpus publish module tests."""

import json
from pathlib import Path

from cfi_contributor.corpus_ingest import ingest_directory, write_manifest
from cfi_contributor.corpus_publish import publish_packages, write_publish_manifest
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient

ROOT = Path(__file__).resolve().parents[2]
BUNDLES = ROOT / "eval" / "benchmarks" / "corpus" / "bundles"


def test_ingest_writes_packages_and_publish_registers(tmp_path: Path) -> None:
    packages_dir = tmp_path / "packages"
    report = ingest_directory(BUNDLES, extract=True, packages_dir=packages_dir)
    assert report.extracted_count >= 1
    assert any(r.package_path for r in report.records)
    write_manifest(report, tmp_path)

    client = RegistryClient.for_app(create_app(RegistryStore()))
    publish_report = publish_packages(packages_dir, client)
    assert publish_report.registered_count >= 1
    manifest = write_publish_manifest(publish_report, tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["registered"] >= 1

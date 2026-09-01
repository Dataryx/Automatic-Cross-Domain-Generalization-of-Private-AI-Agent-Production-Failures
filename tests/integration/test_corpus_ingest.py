"""Private corpus ingestion tests."""

import tempfile
from pathlib import Path

from cfi_contributor.corpus_ingest import (
    bundle_to_incident,
    discover_bundles,
    ingest_directory,
    load_bundle,
    write_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
BUNDLES = ROOT / "eval" / "benchmarks" / "corpus" / "bundles"


def test_discover_benchmark_bundles() -> None:
    paths = discover_bundles(BUNDLES)
    assert len(paths) >= 5


def test_load_and_validate_bundle() -> None:
    bundle = load_bundle(BUNDLES / "bench-001.json")
    assert bundle["schema"] == "incident-bundle/1.0"
    incident = bundle_to_incident(bundle)
    assert incident.incident_id == "bench-001"


def test_ingest_directory_validates_all() -> None:
    report = ingest_directory(BUNDLES)
    assert report.validated_count == len(report.records)
    assert report.validated_count >= 5


def test_ingest_with_extraction() -> None:
    report = ingest_directory(BUNDLES, extract=True)
    assert report.extracted_count > 0


def test_write_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = ingest_directory(BUNDLES)
        path = write_manifest(report, Path(tmp))
        assert path.exists()
        assert path.name == "ingest_manifest.json"

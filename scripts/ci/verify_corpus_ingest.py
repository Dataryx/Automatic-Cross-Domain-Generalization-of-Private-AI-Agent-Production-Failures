#!/usr/bin/env python3
"""Verify local private corpus ingestion (no network egress)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLES = ROOT / "tools/evaluation" / "benchmarks" / "corpus" / "bundles"
OUT = ROOT / "tools/evaluation" / "benchmarks" / "output"


def main() -> int:
    from cfi_contributor.corpus_ingest import ingest_directory, write_manifest

    if not BUNDLES.exists():
        print(f"Missing bundle directory: {BUNDLES}", file=sys.stderr)
        return 1

    report = ingest_directory(BUNDLES, extract=True)
    manifest = write_manifest(report, OUT)
    if report.validated_count != len(report.records):
        print("Not all bundles validated", file=sys.stderr)
        return 1
    if report.extracted_count == 0:
        print("No bundles extracted", file=sys.stderr)
        return 1
    print(
        f"Corpus ingest OK: validated={report.validated_count} "
        f"extracted={report.extracted_count} manifest={manifest}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

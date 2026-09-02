#!/usr/bin/env python3
"""Materialize multi-tenant private corpus layout from benchmark bundles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.corpus_tenants import materialize_tenant_corpus

DEFAULT_SOURCE = ROOT / "eval" / "benchmarks" / "corpus" / "bundles"
DEFAULT_OUTPUT = ROOT / "eval" / "benchmarks" / "corpus" / "tenants"


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize per-tenant incident bundle directories.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tenants", type=int, default=5)
    parser.add_argument("--clean", action="store_true", help="Remove output directory first")
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Missing source bundles: {args.source}", file=sys.stderr)
        return 1

    out = materialize_tenant_corpus(args.source, args.output, tenant_count=args.tenants, clean=args.clean)
    count = len(list(out.rglob("*.json")))
    print(f"Materialized {count} bundles across {args.tenants} tenants -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

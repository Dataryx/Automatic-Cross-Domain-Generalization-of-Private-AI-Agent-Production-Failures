"""Corpus tenant materialization tests."""

import json
import tempfile
from pathlib import Path

from eval.corpus_tenants import materialize_tenant_corpus

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "eval" / "benchmarks" / "corpus" / "bundles"


def test_materialize_tenant_corpus() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = materialize_tenant_corpus(SOURCE, Path(tmp), tenant_count=3)
        tenant_dirs = sorted(p for p in out.iterdir() if p.is_dir())
        assert len(tenant_dirs) == 3
        bundles = list(out.rglob("*.json"))
        assert len(bundles) == 3 * len(list(SOURCE.glob("*.json")))
        sample = json.loads(bundles[0].read_text(encoding="utf-8"))
        assert sample["incident_id"].startswith("tenant-")
        assert sample["metadata"]["tenant_id"].startswith("tenant-")

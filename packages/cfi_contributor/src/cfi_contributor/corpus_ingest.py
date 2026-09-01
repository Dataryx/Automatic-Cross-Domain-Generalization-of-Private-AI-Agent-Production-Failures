"""Local private corpus ingestion — incident bundles never leave contributor zone."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from cfi_contributor.pipeline import ContributorPipeline
from cfi_contributor.replay_profiles import resolve_replay_provider
from cfi_core.schema_validate import validate_incident_bundle
from cfi_core.signing import KeyPair
from cfi_core.wire import Incident, MinimizationConfig, TraceEvent, TypedTrace


@dataclass
class IngestRecord:
    bundle_path: str
    incident_id: str
    validated: bool
    extracted: bool = False
    cfi_id: str | None = None
    error: str | None = None


@dataclass
class IngestReport:
    records: list[IngestRecord] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=lambda: [
        "Raw incident bundles are contributor-local only; this module performs no network egress.",
        "Schema validation is necessary but not sufficient for privacy or causal correctness.",
        "Optional extraction uses structural replay unless a replay profile is supplied.",
    ])

    @property
    def validated_count(self) -> int:
        return sum(1 for r in self.records if r.validated)

    @property
    def extracted_count(self) -> int:
        return sum(1 for r in self.records if r.extracted)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_bundle(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_incident_bundle(payload)
    return cast(dict[str, Any], payload)


def bundle_to_incident(bundle: dict[str, Any]) -> Incident:
    events = [TraceEvent.model_validate(e) for e in bundle["trace"]["events"]]
    return Incident(
        incident_id=bundle["incident_id"],
        initiating_request_digest=bundle["initiating_request_digest"],
        trace=TypedTrace(events=events),
        policy_digest=bundle["policy_digest"],
        initial_state_digest=bundle["initial_state_digest"],
        terminal_state_digest=bundle["terminal_state_digest"],
        expected_outcome=bundle["expected_outcome"],
        observed_outcome=bundle["observed_outcome"],
        severity=float(bundle.get("severity", 0.5)),
        metadata=dict(bundle.get("metadata", {})),
        evidence_store_ref=bundle["evidence_store_ref"],
    )


def bundle_raw_trace(bundle: dict[str, Any]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for idx, event in enumerate(bundle["trace"]["events"]):
        events.append(
            {
                "type": event["event_type"],
                "actor": event["actor"],
                "inputs": event.get("inputs", {}),
                "outputs": event.get("outputs", {}),
                "state_before": event.get("state_before", "unknown"),
                "state_after": event.get("state_after", "unknown"),
                "index": event.get("sequence_index", idx),
            }
        )
    return {"events": events}


def discover_bundles(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("*.json"))


def ingest_directory(
    input_dir: Path,
    *,
    extract: bool = False,
    replay_profile: str | None = None,
    seed: int = 421337,
    key_pair: KeyPair | None = None,
) -> IngestReport:
    """Validate local incident bundles; optionally run contributor extraction."""
    report = IngestReport()
    key = key_pair or KeyPair.generate("corpus-ingest")
    replay = resolve_replay_provider(replay_profile=replay_profile)
    minimization = MinimizationConfig(
        eta=0.9, delta=0.05, lambda_nodes=1.0, lambda_edges=1.0, lambda_literals=1.0, lambda_replay=1.0
    )
    pipeline = ContributorPipeline(key, replay=replay, seed=seed)

    for path in discover_bundles(input_dir):
        record = IngestRecord(bundle_path=str(path), incident_id=path.stem, validated=False)
        try:
            bundle = load_bundle(path)
            record.incident_id = bundle["incident_id"]
            record.validated = True
            if extract:
                incident = bundle_to_incident(bundle)
                raw = bundle_raw_trace(bundle)
                extraction = pipeline.extract_from_incident(
                    incident, raw, minimization, {i: True for i in range(1, 13)}
                )
                if extraction.package and extraction.package.success and extraction.package.cfi is not None:
                    record.extracted = True
                    record.cfi_id = extraction.package.cfi.id
                else:
                    record.error = "extraction_failed"
        except Exception as exc:
            record.error = str(exc)
        report.records.append(record)
    return report


def write_manifest(report: IngestReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "validated": report.validated_count,
        "extracted": report.extracted_count,
        "assumptions": report.assumptions,
        "records": [r.__dict__ for r in report.records],
    }
    path = output_dir / "ingest_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path

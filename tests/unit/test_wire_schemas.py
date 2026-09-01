"""Tests for additional JSON schemas."""

import json
from pathlib import Path

import pytest

from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.schema_validate import (
    load_schema,
    validate_cfi,
    validate_cohort_manifest,
    validate_measurement_spec,
    validate_share_envelope,
)
from cfi_core.signing import KeyPair, Signer
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation import shamir_share


def _signed_cfi_payload() -> dict:
    cfi = build_exception_precedence_cfi()
    key = KeyPair.generate("schema-test")
    sig, chain = Signer(key).sign_package(cfi.model_dump(mode="json"))
    signed = cfi.model_copy(update={"signature": sig, "certificate_chain": chain})
    return signed.model_dump(mode="json")


def test_all_schema_files_exist() -> None:
    root = Path(__file__).resolve().parents[2] / "schemas"
    for name in ("cfi", "incident-bundle", "cohort-manifest", "measurement-spec", "share-envelope"):
        assert (root / name / "1.0" / "schema.json").exists()


def test_cfi_schema_validates_signed_package() -> None:
    validate_cfi(_signed_cfi_payload())


def test_measurement_spec_schema() -> None:
    spec = MeasurementSpec(
        spec_id="spec-1",
        invariant_id="CFI-EXCEPTION-PRECEDENCE-0001",
        simulated_user="stub",
        tool_behavior="stubbed",
        judge="state_first",
        evidence_bar="high",
        trial_count=5,
        aggregation_rule="mean",
        compiler_version="0.1.0",
    )
    payload = {"schema": "measurement-spec/1.0", **spec.model_dump(mode="json")}
    validate_measurement_spec(payload)


def test_cohort_manifest_schema() -> None:
    spec = MeasurementSpec(
        spec_id="spec-1",
        invariant_id="CFI-EXCEPTION-PRECEDENCE-0001",
        simulated_user="stub",
        tool_behavior="stubbed",
        judge="state_first",
        evidence_bar="high",
        trial_count=5,
        aggregation_rule="mean",
        compiler_version="0.1.0",
    )
    manifest = CohortManifest(
        invariant_id="CFI-EXCEPTION-PRECEDENCE-0001",
        eligible_compiler_versions=["0.1.0"],
        measurement_spec=spec,
        trial_count=5,
        clipping_f=10,
        clipping_n=100,
        privacy_budget_epsilon=1.0,
        aggregation_epoch="epoch-2026-01",
        expiration="2026-12-31",
    )
    payload = {
        "schema": "cohort-manifest/1.0",
        **manifest.model_dump(mode="json"),
    }
    payload["measurement_spec"] = {
        "schema": "measurement-spec/1.0",
        **spec.model_dump(mode="json"),
    }
    validate_cohort_manifest(payload)


def test_share_envelope_schema() -> None:
    shares_f = shamir_share(3, threshold=2, num_shares=3)
    shares_n = shamir_share(10, threshold=2, num_shares=3)
    payload = {
        "schema": "share-envelope/1.0",
        "tenant_id_hash": "a" * 64,
        "epoch": "epoch-2026-01",
        "shares_f": [list(s) for s in shares_f],
        "shares_n": [list(s) for s in shares_n],
        "coverage_share": 1.0,
        "measurement_spec_id": "spec-1",
    }
    validate_share_envelope(payload)


def test_load_schema_roundtrip() -> None:
    schema = load_schema("cfi")
    assert schema["$id"].endswith("cfi/1.0")

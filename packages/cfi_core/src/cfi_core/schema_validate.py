"""JSON Schema validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_ROOT = Path(__file__).resolve().parents[4] / "schemas"


def _load_raw(name: str, version: str = "1.0") -> dict[str, Any]:
    path = SCHEMA_ROOT / name / version / "schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_registry() -> Registry:
    resources: list[tuple[str, Resource]] = []
    for name in ("cfi", "incident-bundle", "cohort-manifest", "measurement-spec", "share-envelope"):
        schema = _load_raw(name)
        schema_id = str(schema["$id"])
        resources.append((schema_id, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


_REGISTRY = _schema_registry()


def load_schema(name: str, version: str = "1.0") -> dict[str, Any]:
    return _load_raw(name, version)


def validate_artifact(name: str, payload: dict[str, Any], version: str = "1.0") -> None:
    schema = load_schema(name, version)
    Draft202012Validator(schema, registry=_REGISTRY).validate(payload)


def validate_cfi(payload: dict[str, Any]) -> None:
    validate_artifact("cfi", payload)


def validate_incident_bundle(payload: dict[str, Any]) -> None:
    validate_artifact("incident-bundle", payload)


def validate_measurement_spec(payload: dict[str, Any]) -> None:
    validate_artifact("measurement-spec", payload)


def validate_cohort_manifest(payload: dict[str, Any]) -> None:
    validate_artifact("cohort-manifest", payload)


def validate_share_envelope(payload: dict[str, Any]) -> None:
    validate_artifact("share-envelope", payload)

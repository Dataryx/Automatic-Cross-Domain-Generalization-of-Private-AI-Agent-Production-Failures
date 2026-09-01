"""Schema validation for Appendix A CFI."""

import json
from pathlib import Path

import jsonschema

from cfi_core.examples import build_exception_precedence_cfi


def test_appendix_a_validates() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "cfi" / "1.0" / "schema.json"
    schema = json.loads(schema_path.read_text())
    cfi = build_exception_precedence_cfi()
    payload = cfi.model_dump(mode="json")
    jsonschema.validate(payload, schema)


def test_prohibited_content_rejected() -> None:
    from pydantic import ValidationError

    from cfi_core.examples import build_exception_precedence_cfi

    cfi = build_exception_precedence_cfi()
    blob = cfi.model_dump()
    blob["nodes"][0]["role"] = "customer_refund"
    try:
        from cfi_core.models import CausalFailureInvariant

        CausalFailureInvariant.model_validate(blob)
        raise AssertionError("Should have rejected domain noun")
    except ValidationError:
        pass

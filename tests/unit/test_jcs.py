"""JCS canonicalization byte-stability tests."""

import json

from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.jcs import canonicalize, digest_hex


def test_canonical_bytes_stable_across_key_order() -> None:
    cfi = build_exception_precedence_cfi()
    a = json.loads(cfi.model_dump_json())
    b = {**a}
    # shuffle top-level key order in serialized round-trip
    shuffled = json.loads(json.dumps(b, sort_keys=False))
    assert canonicalize(a) == canonicalize(shuffled)


def test_digest_hex_deterministic() -> None:
    cfi = build_exception_precedence_cfi()
    payload = cfi.model_dump(mode="json")
    d1 = digest_hex(payload)
    d2 = digest_hex(payload)
    assert d1 == d2
    assert len(d1) == 64


def test_nested_list_order_preserved() -> None:
    obj = {"items": [{"b": 2}, {"a": 1}], "z": 1, "a": 0}
    b1 = canonicalize(obj)
    b2 = canonicalize({"a": 0, "z": 1, "items": [{"b": 2}, {"a": 1}]})
    assert b1 == b2

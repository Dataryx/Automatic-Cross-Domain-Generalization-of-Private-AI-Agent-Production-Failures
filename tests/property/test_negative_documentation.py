"""§8.1 negative documentation — product must not overclaim."""

import pathlib


FORBIDDEN_CLAIMS = [
    "causal extraction is solved",
    "canonicalization guarantees confidentiality",
    "dp protects the source incident",
    "better than anonymous",
    "universal vulnerability rate",
]


def test_no_forbidden_privacy_claims_in_docs() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    texts: list[str] = []
    for pattern in ["README.md", "docs/*.md", "packages/**/*.py"]:
        for path in root.glob(pattern):
            if "test" in path.name:
                continue
            texts.append(path.read_text(encoding="utf-8", errors="ignore").lower())
    combined = "\n".join(texts)
    for claim in FORBIDDEN_CLAIMS:
        assert claim not in combined, f"Forbidden claim found: {claim}"

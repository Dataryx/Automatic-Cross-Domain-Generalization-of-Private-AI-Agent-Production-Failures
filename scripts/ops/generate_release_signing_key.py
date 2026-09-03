#!/usr/bin/env python3
"""Generate Ed25519 release signing key for stable manifest attestation."""

from __future__ import annotations

import argparse
from pathlib import Path

from cfi_core.signing import KeyPair


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate CFI-Fed release signing key")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tools/evaluation/keys/release_signing.pem"),
        help="Path to write private key PEM",
    )
    parser.add_argument("--org-id", default="cfi-fed-release", help="Org id embedded in certificate chain")
    args = parser.parse_args()

    key_pair = KeyPair.generate(args.org_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(key_pair.private_pem(), encoding="utf-8")
    pubkey_path = args.output.with_suffix(".pub.pem")
    pubkey_path.write_text(key_pair.public_pem(), encoding="utf-8")
    print(f"Private key: {args.output}")
    print(f"Public key:  {pubkey_path}")
    print("Set CFI_RELEASE_SIGNING_KEY_PATH or CFI_RELEASE_SIGNING_KEY_PEM before make release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

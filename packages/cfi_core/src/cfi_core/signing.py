"""Ed25519 signing and verification (RFC 8032) with certificate chain binding."""

from __future__ import annotations

import base64
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from cfi_core.jcs import canonicalize, digest_hex


@dataclass
class KeyPair:
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey
    org_id: str

    @classmethod
    def generate(cls, org_id: str) -> KeyPair:
        private_key = Ed25519PrivateKey.generate()
        return cls(private_key=private_key, public_key=private_key.public_key(), org_id=org_id)

    @classmethod
    def from_private_pem(cls, pem: str, org_id: str) -> KeyPair:
        private_key = serialization.load_pem_private_key(pem.encode(), password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("PEM must be an Ed25519 private key")
        return cls(private_key=private_key, public_key=private_key.public_key(), org_id=org_id)

    def public_pem(self) -> str:
        return self.public_key.public_bytes(
            encoding=Encoding.PEM,
            format=PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    def private_pem(self) -> str:
        return self.private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        ).decode()


class Signer:
    def __init__(self, key_pair: KeyPair) -> None:
        self._key_pair = key_pair

    def sign_package(self, package: dict[str, object]) -> tuple[str, list[str]]:
        payload = {k: v for k, v in package.items() if k not in ("signature", "certificate_chain")}
        digest = digest_hex(payload)
        sig = self._key_pair.private_key.sign(canonicalize(payload))
        chain = [
            base64.b64encode(self._key_pair.public_key.public_bytes(
                Encoding.Raw, PublicFormat.Raw
            )).decode(),
            self._key_pair.org_id,
            digest,
        ]
        return base64.b64encode(sig).decode(), chain


class Verifier:
    def verify(self, package: dict[str, object]) -> bool:
        sig_b64 = package.get("signature")
        chain = package.get("certificate_chain")
        if not isinstance(sig_b64, str) or not isinstance(chain, list) or not chain:
            return False
        payload = {k: v for k, v in package.items() if k not in ("signature", "certificate_chain")}
        try:
            pub_raw = base64.b64decode(str(chain[0]))
            public_key = Ed25519PublicKey.from_public_bytes(pub_raw)
            public_key.verify(base64.b64decode(sig_b64), canonicalize(payload))
            return True
        except Exception:
            return False

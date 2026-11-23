"""L6 signed contracts: Ed25519 over canonical JSON. An unsigned or modified contract is refused (P5)."""

import base64
import copy
import json
from collections.abc import Mapping
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.security.contracts import Contract


class ContractSignatureError(Exception):
    """Signature missing, from an untrusted key, or not matching the contract body."""


def canonical_payload(doc: Mapping[str, Any]) -> bytes:
    """Everything except `signature`, as sorted compact JSON. Raises TypeError/ValueError on non-JSON values."""
    body = {k: v for k, v in doc.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sign_contract(doc: Mapping[str, Any], private_key: Ed25519PrivateKey, key_id: str) -> dict[str, Any]:
    signature = base64.b64encode(private_key.sign(canonical_payload(doc))).decode()
    body = {k: v for k, v in doc.items() if k != "signature"}
    return {**body, "signature": {"alg": "ed25519", "key_id": key_id, "value": signature}}


def verify_contract(doc: Mapping[str, Any], trusted_keys: Mapping[str, Ed25519PublicKey]) -> None:
    sig = doc.get("signature")
    if not isinstance(sig, dict) or sig.get("alg") != "ed25519":
        raise ContractSignatureError("missing or non-ed25519 signature")
    key_id = sig.get("key_id")
    key = trusted_keys.get(key_id) if isinstance(key_id, str) else None
    if key is None:
        raise ContractSignatureError(f"untrusted key_id {key_id!r}")
    try:
        key.verify(base64.b64decode(sig.get("value", ""), validate=True), canonical_payload(doc))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise ContractSignatureError(f"signature check failed for {doc.get('playbook_id')!r}") from exc


def load_contract(doc: Mapping[str, Any], trusted_keys: Mapping[str, Ed25519PublicKey]) -> Contract:
    """The only way retrieval should obtain a Contract: verify first, then parse a private copy."""
    verify_contract(doc, trusted_keys)
    body = copy.deepcopy({k: v for k, v in doc.items() if k != "signature"})
    return Contract.model_validate(body)

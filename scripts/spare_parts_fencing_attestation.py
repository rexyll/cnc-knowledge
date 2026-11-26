"""Canonical HMAC fencing attestations for trusted local coordinator/provider contracts."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from typing import Any


class FencingAttestationError(ValueError):
    """A fencing attestation is malformed, untrusted, mismatched or expired."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(value: str) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise FencingAttestationError("fencing attestation base64url component is invalid")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _key_bytes(secret: str | bytes) -> bytes:
    if isinstance(secret, str):
        result = secret.encode("utf-8")
    elif isinstance(secret, bytes):
        result = secret
    else:
        raise FencingAttestationError("fencing attestation key must be bytes or text")
    if len(result) < 32:
        raise FencingAttestationError("HMAC-SHA256 fencing attestation key must contain at least 32 bytes")
    return result


def canonical_claims(claims: dict[str, Any]) -> bytes:
    if not isinstance(claims, dict):
        raise FencingAttestationError("fencing attestation claims must be a JSON object")
    try:
        return json.dumps(
            claims, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FencingAttestationError("fencing attestation claims are not canonical JSON values") from exc


def create_fencing_attestation(
    claims: dict[str, Any], *, key_id: str, secret: str | bytes
) -> str:
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id):
        raise FencingAttestationError("fencing attestation key ID is invalid")
    payload = _b64url(canonical_claims(claims))
    signing_input = ("cnc-ch17-fencing-attestation.v1." + key_id + "." + payload).encode("ascii")
    signature = hmac.new(_key_bytes(secret), signing_input, hashlib.sha256).digest()
    return "v1." + key_id + "." + payload + "." + _b64url(signature)


def verify_fencing_attestation_signature(
    token: str, *, trusted_keys: dict[str, str | bytes]
) -> tuple[dict[str, Any], str]:
    if not isinstance(token, str) or len(token) > 8192:
        raise FencingAttestationError("fencing attestation is missing or exceeds the size limit")
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != "v1":
        raise FencingAttestationError("fencing attestation version or structure is invalid")
    _, key_id, payload, signature_text = parts
    secret = trusted_keys.get(key_id)
    if secret is None:
        raise FencingAttestationError("fencing attestation key ID is not configured")
    signing_input = ("cnc-ch17-fencing-attestation.v1." + key_id + "." + payload).encode("ascii")
    expected = hmac.new(_key_bytes(secret), signing_input, hashlib.sha256).digest()
    supplied = _unb64url(signature_text)
    if not hmac.compare_digest(expected, supplied):
        raise FencingAttestationError("fencing attestation signature is invalid")
    try:
        claims = json.loads(_unb64url(payload).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FencingAttestationError("fencing attestation claims cannot be decoded") from exc
    if not isinstance(claims, dict):
        raise FencingAttestationError("fencing attestation claims must be a JSON object")
    if claims.get("v") != 1 or claims.get("kid") != key_id:
        raise FencingAttestationError("fencing attestation claims version or key ID mismatch")
    return claims, key_id

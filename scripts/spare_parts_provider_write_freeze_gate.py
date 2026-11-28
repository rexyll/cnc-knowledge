#!/usr/bin/env python3
"""Signed monotonic Provider write-freeze control command contract.

The verifier authenticates a short-lived command; the Provider must persist
its generation and check it inside the same transaction as every mutation.
This module alone does not enforce a freeze.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


FREEZE_GATE_ENVELOPE_FORMAT = "ch17-provider-write-freeze-command-envelope-v2"
FREEZE_GATE_CLAIMS_FORMAT = "ch17-provider-write-freeze-command-v2"
FREEZE_GATE_SIGNATURE_DOMAIN = b"cnc-knowledge-provider-write-freeze-command-v2\x00"


class ProviderWriteFreezeCommandError(ValueError):
    """A signed Provider freeze command is malformed, untrusted or stale."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProviderWriteFreezeCommandError("freeze command is not canonical JSON") from exc


def verify_provider_write_freeze_command(
    envelope: dict[str, Any],
    trusted_public_keys: dict[str, Any],
    *,
    expected_provider_id: str,
    expected_tenant_id: str,
    now_unix: float,
    maximum_lifetime_seconds: float = 60.0,
) -> tuple[dict[str, Any], str, str]:
    if not isinstance(envelope, dict) or set(envelope) != {
        "format", "command", "signature"
    } or envelope.get("format") != FREEZE_GATE_ENVELOPE_FORMAT:
        raise ProviderWriteFreezeCommandError("freeze command envelope schema mismatch")
    claims = envelope.get("command")
    if not isinstance(claims, dict) or set(claims) != {
        "format", "issuer_id", "provider_id", "tenant_id", "scope",
        "action", "freeze_id", "generation", "issued_at_unix", "expires_at_unix",
        "coordinator_namespace", "leader_id", "leader_epoch", "leader_lease_id",
        "leader_lease_expires_at_unix",
    } or claims.get("format") != FREEZE_GATE_CLAIMS_FORMAT:
        raise ProviderWriteFreezeCommandError("freeze command claims schema mismatch")
    signature = envelope.get("signature")
    if not isinstance(signature, dict) or set(signature) != {
        "algorithm", "key_id", "value_base64"
    } or signature.get("algorithm") != "Ed25519":
        raise ProviderWriteFreezeCommandError("freeze command signature schema mismatch")
    key_id = signature.get("key_id")
    if not isinstance(key_id, str) or not key_id.strip():
        raise ProviderWriteFreezeCommandError("freeze command key ID is invalid")
    public_key = trusted_public_keys.get(key_id)
    if public_key is None:
        raise ProviderWriteFreezeCommandError("freeze command signer is not trusted")
    try:
        signature_bytes = base64.b64decode(signature["value_base64"], validate=True)
    except (ValueError, TypeError, KeyError) as exc:
        raise ProviderWriteFreezeCommandError("freeze command signature is invalid base64") from exc
    if len(signature_bytes) != 64:
        raise ProviderWriteFreezeCommandError("freeze command signature length is invalid")
    if (
        not isinstance(expected_provider_id, str) or not expected_provider_id.strip()
        or claims.get("provider_id") != expected_provider_id
        or claims.get("tenant_id") != expected_tenant_id
    ):
        raise ProviderWriteFreezeCommandError("freeze command Provider or tenant binding mismatch")
    for field in ("issuer_id", "scope", "freeze_id", "coordinator_namespace", "leader_id"):
        value = claims.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ProviderWriteFreezeCommandError(f"freeze command {field} is invalid")
    if claims["action"] not in {"FREEZE", "UNFREEZE"}:
        raise ProviderWriteFreezeCommandError("freeze command action is invalid")
    generation = claims.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation <= 0:
        raise ProviderWriteFreezeCommandError("freeze command generation must be positive")
    leader_epoch = claims.get("leader_epoch")
    leader_lease_id = claims.get("leader_lease_id")
    if not isinstance(leader_epoch, int) or isinstance(leader_epoch, bool) or leader_epoch <= 0:
        raise ProviderWriteFreezeCommandError("Coordinator Leader epoch must be positive")
    if not isinstance(leader_lease_id, int) or isinstance(leader_lease_id, bool) or leader_lease_id <= 0:
        raise ProviderWriteFreezeCommandError("Coordinator native Leader Lease ID must be positive")
    issued = claims.get("issued_at_unix")
    expires = claims.get("expires_at_unix")
    lease_expires = claims.get("leader_lease_expires_at_unix")
    if any(
        not isinstance(value, (int, float)) or isinstance(value, bool)
        or not math.isfinite(float(value))
        for value in (issued, expires, lease_expires, now_unix, maximum_lifetime_seconds)
    ):
        raise ProviderWriteFreezeCommandError("freeze command timestamps are invalid")
    if (
        float(issued) > float(now_unix) + 5.0
        or float(expires) <= float(now_unix)
        or float(expires) <= float(issued)
        or float(expires) - float(issued) > float(maximum_lifetime_seconds)
        or float(lease_expires) <= float(now_unix)
        or float(expires) > float(lease_expires)
    ):
        raise ProviderWriteFreezeCommandError("freeze command or Coordinator Leader Lease is expired or outside its validity window")
    if not isinstance(public_key, Ed25519PublicKey):
        raise ProviderWriteFreezeCommandError("configured freeze command key is not Ed25519")
    try:
        public_key.verify(
            signature_bytes,
            FREEZE_GATE_SIGNATURE_DOMAIN + _canonical(claims),
        )
    except (InvalidSignature, ValueError) as exc:
        raise ProviderWriteFreezeCommandError("freeze command signature verification failed") from exc
    # Bind receipts to the exact signed envelope, not only equivalent claims.
    return claims, key_id, hashlib.sha256(_canonical(envelope)).hexdigest()


def sign_provider_write_freeze_command(
    claims: dict[str, Any], *, key_id: str, private_key: Any
) -> dict[str, Any]:
    """Small signer helper for deterministic fixtures and offline tooling."""
    signature = private_key.sign(FREEZE_GATE_SIGNATURE_DOMAIN + _canonical(claims))
    return {
        "format": FREEZE_GATE_ENVELOPE_FORMAT,
        "command": claims,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "value_base64": base64.b64encode(signature).decode("ascii"),
        },
    }

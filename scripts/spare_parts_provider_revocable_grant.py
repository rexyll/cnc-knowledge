#!/usr/bin/env python3
"""Signed Provider-native FENCE / ACTIVATE commands for local reference validation."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from typing import Any

from scripts.spare_parts_fencing_attestation import _load_ed25519_public_key

ENVELOPE_FORMAT = "ch17-provider-revocable-grant-envelope-v1"
CLAIMS_FORMAT = "ch17-provider-revocable-grant-command-v1"
SIGNING_DOMAIN = b"cnc-knowledge-provider-revocable-grant-command-v1\x00"
MAX_SQLITE_INTEGER = (1 << 63) - 1
MAX_GRANT_LIFETIME_SECONDS = 300.0
CLAIM_FIELDS = {
    "format", "issuer_id", "provider_id", "tenant_id", "scope", "action",
    "grant_id", "generation", "issued_at_unix", "expires_at_unix",
    "coordinator_namespace", "leader_id", "leader_epoch", "leader_lease_id",
    "leader_lease_expires_at_unix", "fence_command_sha256",
}


class ProviderGrantCommandError(ValueError):
    """A signed Provider grant command is malformed, untrusted or stale."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProviderGrantCommandError("Provider grant command is not canonical JSON") from exc


def _signing_input(key_id: str, claims: dict[str, Any]) -> bytes:
    return SIGNING_DOMAIN + key_id.encode("ascii") + b"." + _canonical(claims)


def sign_provider_grant_command(
    claims: dict[str, Any], *, key_id: str, private_key: Any
) -> dict[str, Any]:
    """Sign a FENCE or ACTIVATE claim set with an Ed25519 private key."""
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id):
        raise ProviderGrantCommandError("Provider grant signer key ID is invalid")
    if not isinstance(claims, dict) or claims.get("format") != CLAIMS_FORMAT:
        raise ProviderGrantCommandError("Provider grant claims format is invalid")
    try:
        signature = private_key.sign(_signing_input(key_id, claims))
    except Exception as exc:
        raise ProviderGrantCommandError("Provider grant signing failed") from exc
    if not isinstance(signature, bytes) or len(signature) != 64:
        raise ProviderGrantCommandError("Provider grant signer returned an invalid signature")
    return {
        "format": ENVELOPE_FORMAT,
        "command": claims,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "value_base64": base64.b64encode(signature).decode("ascii"),
        },
    }


def verify_provider_grant_command(
    envelope: dict[str, Any], trusted_public_keys: dict[str, Any], *,
    expected_provider_id: str, expected_tenant_id: str, now_unix: float,
) -> tuple[dict[str, Any], str, str]:
    """Verify exact schema, signature, scope, monotonic identity and time bounds."""
    if not isinstance(envelope, dict) or set(envelope) != {"format", "command", "signature"}:
        raise ProviderGrantCommandError("Provider grant envelope schema mismatch")
    if envelope.get("format") != ENVELOPE_FORMAT:
        raise ProviderGrantCommandError("Provider grant envelope format is unsupported")
    claims = envelope.get("command")
    if not isinstance(claims, dict) or set(claims) != CLAIM_FIELDS or claims.get("format") != CLAIMS_FORMAT:
        raise ProviderGrantCommandError("Provider grant claims schema mismatch")
    signature = envelope.get("signature")
    if not isinstance(signature, dict) or set(signature) != {"algorithm", "key_id", "value_base64"}:
        raise ProviderGrantCommandError("Provider grant signature schema mismatch")
    key_id = signature.get("key_id")
    if signature.get("algorithm") != "Ed25519" or not isinstance(key_id, str) or not key_id.strip():
        raise ProviderGrantCommandError("Provider grant signature algorithm or key ID is invalid")
    public_key = trusted_public_keys.get(key_id)
    if public_key is None:
        raise ProviderGrantCommandError("Provider grant signer is not trusted")
    try:
        supplied = base64.b64decode(signature["value_base64"], validate=True)
        if len(supplied) != 64:
            raise ValueError("invalid signature length")
        _load_ed25519_public_key(public_key).verify(supplied, _signing_input(key_id, claims))
    except Exception as exc:
        raise ProviderGrantCommandError("Provider grant signature is invalid") from exc
    if (
        not isinstance(expected_provider_id, str) or not expected_provider_id.strip()
        or claims.get("provider_id") != expected_provider_id
        or claims.get("tenant_id") != expected_tenant_id
    ):
        raise ProviderGrantCommandError("Provider grant Provider or tenant binding mismatch")
    for field in ("issuer_id", "scope", "grant_id", "coordinator_namespace", "leader_id"):
        value = claims.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ProviderGrantCommandError(f"Provider grant {field} is invalid")
    scope_parts = claims["scope"].split("/")
    if (
        claims["scope"].startswith("/") or claims["scope"].endswith("/")
        or any(part in {"", ".", ".."} for part in scope_parts)
        or any(ord(ch) < 32 for ch in claims["scope"])
    ):
        raise ProviderGrantCommandError("Provider grant scope is not canonical")
    namespace = claims["coordinator_namespace"]
    namespace_parts = namespace.strip("/").split("/")
    if (
        not namespace.startswith("/") or not namespace.endswith("/")
        or "//" in namespace or any(part in {"", ".", ".."} for part in namespace_parts)
        or any(ch.isspace() for ch in namespace)
    ):
        raise ProviderGrantCommandError("Coordinator namespace is not a canonical absolute prefix")
    if claims["action"] not in {"FENCE", "ACTIVATE"}:
        raise ProviderGrantCommandError("Provider grant action must be FENCE or ACTIVATE")
    for field in ("generation", "leader_epoch", "leader_lease_id"):
        value = claims[field]
        if (
            not isinstance(value, int) or isinstance(value, bool)
            or value <= 0 or value > MAX_SQLITE_INTEGER
        ):
            raise ProviderGrantCommandError(
                f"Provider grant {field} must be a positive SQLite-safe integer"
            )
    times = (
        claims["issued_at_unix"], claims["expires_at_unix"],
        claims["leader_lease_expires_at_unix"], now_unix,
    )
    if any(
        not isinstance(value, (int, float)) or isinstance(value, bool)
        or not math.isfinite(float(value)) or float(value) < 0
        for value in times
    ):
        raise ProviderGrantCommandError("Provider grant time claims are invalid")
    issued, expires, lease_expires, now = (float(v) for v in times)
    if (
        issued > now + 5.0 or expires <= now or expires <= issued
        or expires > lease_expires or lease_expires <= now
        or expires - issued > MAX_GRANT_LIFETIME_SECONDS
    ):
        raise ProviderGrantCommandError("Provider grant is expired or exceeds its Coordinator Lease")
    fence_digest = claims["fence_command_sha256"]
    if claims["action"] == "FENCE":
        if fence_digest is not None:
            raise ProviderGrantCommandError("FENCE command must not reference another FENCE receipt")
    elif not isinstance(fence_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", fence_digest):
        raise ProviderGrantCommandError("ACTIVATE command must bind an exact FENCE receipt digest")
    digest = hashlib.sha256(_canonical(envelope)).hexdigest()
    return claims, key_id, digest

#!/usr/bin/env python3
"""Signed Provider-native FENCE / ACTIVATE receipt evidence for CH17 local references."""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ENVELOPE_FORMAT = "cnc-provider-grant-receipt-envelope-v1"
CLAIMS_FORMAT = "cnc-provider-grant-receipt-v1"
SIGNING_DOMAIN = b"cnc-provider-grant-receipt-v1\x00"
MAX_SQLITE_INTEGER = (1 << 63) - 1
MAX_CLOCK_SKEW_SECONDS = 5.0
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_KEY_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_CLAIM_FIELDS = {
    "format", "provider_id", "tenant_id", "scope", "action", "grant_id",
    "generation", "command_sha256", "fence_command_sha256", "result_state",
    "coordinator_namespace", "leader_id", "leader_epoch", "native_lease_id",
    "native_lease_expires_at_unix", "command_issued_at_unix",
    "command_expires_at_unix", "applied_at_unix",
}
_ENVELOPE_FIELDS = {"format", "receipt", "signature"}
_SIGNATURE_FIELDS = {"algorithm", "key_id", "value_base64"}


class ProviderGrantReceiptError(ValueError):
    """A Provider Grant receipt is malformed, unauthenticated or inconsistent."""


@dataclass(frozen=True)
class ProviderReceiptTrustKey:
    provider_id: str
    key_id: str
    public_key: bytes
    public_key_sha256: str
    status: str
    not_before: float
    not_after: float | None
    retiring_effective_at: float | None
    revocation_effective_at: float | None
    trust_revision: int


@dataclass(frozen=True)
class VerifiedProviderGrantReceipt:
    provider_id: str
    tenant_id: str
    scope: str
    action: str
    grant_id: str
    generation: int
    command_sha256: str
    fence_command_sha256: str | None
    result_state: str
    coordinator_namespace: str
    leader_id: str
    leader_epoch: int
    native_lease_id: int
    native_lease_expires_at_unix: float
    command_issued_at_unix: float
    command_expires_at_unix: float
    applied_at_unix: float
    signer_key_id: str
    signer_public_key_sha256: str
    trust_revision: int
    receipt_digest: str
    canonical_envelope: bytes
    claims: Mapping[str, Any]


def canonical_receipt_json(value: Any) -> bytes:
    """Return RFC 8785 canonical UTF-8 bytes; reject unsupported JSON values."""
    try:
        return rfc8785.dumps(value)
    except (TypeError, ValueError, rfc8785.CanonicalizationError) as exc:
        raise ProviderGrantReceiptError("Provider receipt is not valid RFC 8785 JSON") from exc


def _signing_input(key_id: str, claims: dict[str, Any]) -> bytes:
    return SIGNING_DOMAIN + key_id.encode("ascii") + b"." + canonical_receipt_json(claims)


def _text(value: Any, field: str, *, max_length: int = 256) -> str:
    if (
        not isinstance(value, str) or not value or len(value) > max_length
        or value.strip() != value or any(ord(ch) < 32 for ch in value)
    ):
        raise ProviderGrantReceiptError(f"Provider receipt {field} is invalid")
    return value


def _integer(value: Any, field: str) -> int:
    if (
        not isinstance(value, int) or isinstance(value, bool)
        or value < 1 or value > MAX_SQLITE_INTEGER
    ):
        raise ProviderGrantReceiptError(
            f"Provider receipt {field} must be a SQLite-safe positive integer"
        )
    return value


def _timestamp(value: Any, field: str) -> float:
    if (
        not isinstance(value, (int, float)) or isinstance(value, bool)
        or not math.isfinite(float(value)) or float(value) < 0
    ):
        raise ProviderGrantReceiptError(f"Provider receipt {field} must be finite and non-negative")
    return float(value)


def _digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ProviderGrantReceiptError(
            f"Provider receipt {field} must be a lowercase SHA-256 digest"
        )
    return value


def _validate_claims(claims: Any) -> dict[str, Any]:
    if not isinstance(claims, dict) or set(claims) != _CLAIM_FIELDS:
        raise ProviderGrantReceiptError("Provider receipt claims schema mismatch")
    if claims.get("format") != CLAIMS_FORMAT:
        raise ProviderGrantReceiptError("Provider receipt claims format is unsupported")

    for field in ("provider_id", "tenant_id", "grant_id", "leader_id"):
        value = _text(claims.get(field), field)
        if not _ID_RE.fullmatch(value):
            raise ProviderGrantReceiptError(f"Provider receipt {field} is invalid")

    scope = _text(claims.get("scope"), "scope")
    scope_parts = scope.split("/")
    if scope.startswith("/") or scope.endswith("/") or any(
        part in {"", ".", ".."} for part in scope_parts
    ):
        raise ProviderGrantReceiptError("Provider receipt scope is not canonical")

    namespace = _text(claims.get("coordinator_namespace"), "coordinator_namespace")
    if not namespace.startswith("/") or not namespace.endswith("/") or "//" in namespace:
        raise ProviderGrantReceiptError("Provider receipt Coordinator namespace is not isolated")
    namespace_parts = namespace.strip("/").split("/")
    if (
        len(namespace_parts) != 4
        or namespace_parts[:3] != ["cnc", "migration", "isolated"]
        or not _ID_RE.fullmatch(namespace_parts[3])
    ):
        raise ProviderGrantReceiptError("Provider receipt Coordinator namespace is not isolated")

    action = claims.get("action")
    if not isinstance(action, str) or action not in {"FENCE", "ACTIVATE"}:
        raise ProviderGrantReceiptError("Provider receipt action must be FENCE or ACTIVATE")
    result_state = claims.get("result_state")
    expected_state = "FENCED" if action == "FENCE" else "ACTIVE"
    if result_state != expected_state:
        raise ProviderGrantReceiptError("Provider receipt result state does not match its action")

    _integer(claims.get("generation"), "generation")
    _integer(claims.get("leader_epoch"), "leader_epoch")
    _integer(claims.get("native_lease_id"), "native_lease_id")
    _digest(claims.get("command_sha256"), "command_sha256")

    fence_digest = claims.get("fence_command_sha256")
    if action == "FENCE":
        if fence_digest is not None:
            raise ProviderGrantReceiptError("FENCE receipt must not reference a prior FENCE command")
    else:
        _digest(fence_digest, "fence_command_sha256")

    lease_expiry = _timestamp(
        claims.get("native_lease_expires_at_unix"), "native_lease_expires_at_unix"
    )
    issued = _timestamp(claims.get("command_issued_at_unix"), "command_issued_at_unix")
    expires = _timestamp(claims.get("command_expires_at_unix"), "command_expires_at_unix")
    applied = _timestamp(claims.get("applied_at_unix"), "applied_at_unix")
    if expires <= issued or expires > lease_expiry:
        raise ProviderGrantReceiptError("Provider receipt command validity exceeds its Leader Lease")
    if applied < issued - MAX_CLOCK_SKEW_SECONDS or applied > expires:
        raise ProviderGrantReceiptError("Provider receipt applied time is outside the signed command window")
    return dict(claims)


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProviderGrantReceiptError("Provider receipt JSON contains a duplicate object key")
        result[key] = value
    return result


def parse_receipt_envelope(envelope: dict[str, Any] | bytes | str) -> dict[str, Any]:
    """Parse an envelope, rejecting duplicate JSON keys and non-finite constants."""
    if isinstance(envelope, dict):
        parsed = envelope
    elif isinstance(envelope, bytes):
        try:
            raw = envelope.decode("utf-8", errors="strict")
            parsed = json.loads(
                raw, object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ProviderGrantReceiptError(f"invalid JSON constant: {value}")
                ),
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderGrantReceiptError("Provider receipt envelope is not valid UTF-8 JSON") from exc
    elif isinstance(envelope, str):
        try:
            parsed = json.loads(
                envelope, object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ProviderGrantReceiptError(f"invalid JSON constant: {value}")
                ),
            )
        except json.JSONDecodeError as exc:
            raise ProviderGrantReceiptError("Provider receipt envelope is not valid JSON") from exc
    else:
        raise ProviderGrantReceiptError("Provider receipt envelope must be a JSON object or encoded JSON")
    if not isinstance(parsed, dict) or set(parsed) != _ENVELOPE_FIELDS:
        raise ProviderGrantReceiptError("Provider receipt envelope schema mismatch")
    if parsed.get("format") != ENVELOPE_FORMAT:
        raise ProviderGrantReceiptError("Provider receipt envelope format is unsupported")
    _validate_claims(parsed.get("receipt"))
    signature = parsed.get("signature")
    if not isinstance(signature, dict) or set(signature) != _SIGNATURE_FIELDS:
        raise ProviderGrantReceiptError("Provider receipt signature schema mismatch")
    if signature.get("algorithm") != "Ed25519":
        raise ProviderGrantReceiptError("Provider receipt signature algorithm is unsupported")
    key_id = signature.get("key_id")
    if not isinstance(key_id, str) or not _KEY_ID_RE.fullmatch(key_id):
        raise ProviderGrantReceiptError("Provider receipt signer key ID is invalid")
    encoded = signature.get("value_base64")
    if not isinstance(encoded, str):
        raise ProviderGrantReceiptError("Provider receipt signature value is invalid")
    try:
        raw_signature = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ProviderGrantReceiptError("Provider receipt signature is not strict base64") from exc
    if len(raw_signature) != 64:
        raise ProviderGrantReceiptError("Provider receipt Ed25519 signature must contain 64 bytes")
    return parsed


def sign_provider_grant_receipt(
    claims: dict[str, Any], *, key_id: str, private_key: Any
) -> dict[str, Any]:
    """Sign validated receipt claims with a Provider-owned Ed25519 private key."""
    validated = _validate_claims(claims)
    if not isinstance(key_id, str) or not _KEY_ID_RE.fullmatch(key_id):
        raise ProviderGrantReceiptError("Provider receipt signer key ID is invalid")
    try:
        signature = private_key.sign(_signing_input(key_id, validated))
    except Exception as exc:
        raise ProviderGrantReceiptError("Provider receipt Ed25519 signing failed") from exc
    if not isinstance(signature, bytes) or len(signature) != 64:
        raise ProviderGrantReceiptError("Provider receipt signer returned an invalid signature")
    return {
        "format": ENVELOPE_FORMAT,
        "receipt": validated,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "value_base64": base64.b64encode(signature).decode("ascii"),
        },
    }


def verify_provider_grant_receipt(
    envelope: dict[str, Any] | bytes | str,
    trust_key: ProviderReceiptTrustKey,
    *,
    expected_claims: Mapping[str, Any],
    now_unix: float | None = None,
) -> VerifiedProviderGrantReceipt:
    """Verify Provider signature, key lifecycle and every expected reservation claim."""
    parsed = parse_receipt_envelope(envelope)
    claims = _validate_claims(parsed["receipt"])
    signature = parsed["signature"]
    key_id = signature["key_id"]

    if not isinstance(trust_key, ProviderReceiptTrustKey):
        raise ProviderGrantReceiptError("a trusted Provider receipt key is required")
    if trust_key.provider_id != claims["provider_id"] or trust_key.key_id != key_id:
        raise ProviderGrantReceiptError("Provider receipt signer identity does not match the trust registry")
    if (
        not isinstance(trust_key.public_key, bytes) or len(trust_key.public_key) != 32
        or hashlib.sha256(trust_key.public_key).hexdigest() != trust_key.public_key_sha256
    ):
        raise ProviderGrantReceiptError("Provider receipt trusted public-key fingerprint mismatch")
    if not isinstance(trust_key.status, str) or trust_key.status not in {
        "ACTIVE", "RETIRING", "REVOKED"
    }:
        raise ProviderGrantReceiptError("Provider receipt signing key status is unsupported")
    not_before = _timestamp(trust_key.not_before, "key_not_before")
    not_after = (
        _timestamp(trust_key.not_after, "key_not_after")
        if trust_key.not_after is not None else None
    )
    if not_after is not None and not_after <= not_before:
        raise ProviderGrantReceiptError("Provider receipt key validity interval is invalid")
    if (
        not isinstance(trust_key.trust_revision, int)
        or isinstance(trust_key.trust_revision, bool)
        or trust_key.trust_revision < 1
        or trust_key.trust_revision > MAX_SQLITE_INTEGER
    ):
        raise ProviderGrantReceiptError("Provider receipt trust revision is invalid")

    applied = claims["applied_at_unix"]
    now = time.time() if now_unix is None else _timestamp(now_unix, "verification_time_unix")
    if applied > now + MAX_CLOCK_SKEW_SECONDS:
        raise ProviderGrantReceiptError("Provider receipt applied time is in the future")
    if applied < not_before:
        raise ProviderGrantReceiptError("Provider receipt was signed before the key validity window")
    if not_after is not None and applied >= not_after:
        raise ProviderGrantReceiptError("Provider receipt was signed after the key validity window")
    if trust_key.status == "REVOKED":
        effective = trust_key.revocation_effective_at
        if effective is None or applied >= float(effective):
            raise ProviderGrantReceiptError("Provider receipt signing key was revoked at the applied time")
    if trust_key.status in {"RETIRING", "REVOKED"}:
        retirement = trust_key.retiring_effective_at
        if retirement is None or applied >= float(retirement):
            raise ProviderGrantReceiptError(
                "Provider receipt was applied after the key stopped issuing new receipts"
            )

    expected = dict(expected_claims)
    if not expected or any(field not in _CLAIM_FIELDS for field in expected):
        raise ProviderGrantReceiptError("expected Provider receipt claims are invalid")
    for field, value in expected.items():
        if claims.get(field) != value:
            if field == "command_sha256":
                raise ProviderGrantReceiptError("Provider receipt command digest does not match reservation")
            raise ProviderGrantReceiptError(f"Provider receipt {field} does not match reservation")

    raw_signature = base64.b64decode(signature["value_base64"], validate=True)
    try:
        Ed25519PublicKey.from_public_bytes(trust_key.public_key).verify(
            raw_signature, _signing_input(key_id, claims)
        )
    except (InvalidSignature, ValueError) as exc:
        raise ProviderGrantReceiptError("Provider receipt Ed25519 signature verification failed") from exc

    canonical_envelope = canonical_receipt_json(parsed)
    receipt_digest = hashlib.sha256(canonical_envelope).hexdigest()
    return VerifiedProviderGrantReceipt(
        provider_id=claims["provider_id"],
        tenant_id=claims["tenant_id"],
        scope=claims["scope"],
        action=claims["action"],
        grant_id=claims["grant_id"],
        generation=claims["generation"],
        command_sha256=claims["command_sha256"],
        fence_command_sha256=claims["fence_command_sha256"],
        result_state=claims["result_state"],
        coordinator_namespace=claims["coordinator_namespace"],
        leader_id=claims["leader_id"],
        leader_epoch=claims["leader_epoch"],
        native_lease_id=claims["native_lease_id"],
        native_lease_expires_at_unix=claims["native_lease_expires_at_unix"],
        command_issued_at_unix=claims["command_issued_at_unix"],
        command_expires_at_unix=claims["command_expires_at_unix"],
        applied_at_unix=claims["applied_at_unix"],
        signer_key_id=key_id,
        signer_public_key_sha256=trust_key.public_key_sha256,
        trust_revision=trust_key.trust_revision,
        receipt_digest=receipt_digest,
        canonical_envelope=canonical_envelope,
        claims=MappingProxyType(claims),
    )

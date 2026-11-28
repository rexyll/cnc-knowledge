#!/usr/bin/env python3
"""Verify signed, read-only Provider fencing evidence before reconciliation.

This module verifies an Ed25519 signature against an operator-supplied trust
store, then delegates all freshness/scope/floor checks to the existing
read-only reconciler. It never contacts or mutates a Provider.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from scripts.spare_parts_sqlite_provider_fencing_reconciliation import (
    ProviderFencingReconciliationError,
    _canonical,
    validate_provider_fencing_reconciliation,
)


SIGNATURE_DOMAIN = b"cnc-knowledge-provider-fencing-evidence-v1\x00"


def _decode_base64(value: Any, field: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ProviderFencingReconciliationError(f"{field} must be non-empty base64")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ProviderFencingReconciliationError(f"{field} is invalid base64") from exc


def validate_signed_provider_fencing_reconciliation(
    candidate: dict[str, Any],
    envelope: dict[str, Any],
    trust_store: dict[str, Any],
    *,
    now_unix: float,
    maximum_age_seconds: float = 300.0,
) -> dict[str, Any]:
    """Verify a detached Ed25519 signature and reconcile its evidence.

    The trust store is caller-supplied. Its provenance and protection are an
    external responsibility; a valid signature alone is not a freeze proof.
    """
    if not isinstance(envelope, dict) or set(envelope) != {
        "format", "evidence", "signature"
    }:
        raise ProviderFencingReconciliationError("signed Provider envelope schema mismatch")
    if envelope.get("format") != "ch17-provider-fencing-signed-evidence-v1":
        raise ProviderFencingReconciliationError("unsupported signed Provider evidence format")
    if not isinstance(trust_store, dict) or set(trust_store) != {"format", "keys"}:
        raise ProviderFencingReconciliationError("Provider trust store schema mismatch")
    if trust_store.get("format") != "ch17-provider-fencing-trust-store-v1":
        raise ProviderFencingReconciliationError("unsupported Provider trust store format")
    keys = trust_store.get("keys")
    if not isinstance(keys, dict) or not keys:
        raise ProviderFencingReconciliationError("Provider trust store has no trusted keys")

    signature_record = envelope.get("signature")
    if not isinstance(signature_record, dict) or set(signature_record) != {
        "algorithm", "key_id", "value_base64"
    }:
        raise ProviderFencingReconciliationError("Provider signature schema mismatch")
    if signature_record.get("algorithm") != "Ed25519":
        raise ProviderFencingReconciliationError("unsupported Provider signature algorithm")
    key_id = signature_record.get("key_id")
    if not isinstance(key_id, str) or not key_id.strip() or key_id not in keys:
        raise ProviderFencingReconciliationError("Provider signing key is not trusted")

    key_record = keys[key_id]
    if not isinstance(key_record, dict) or set(key_record) != {
        "algorithm", "public_key_base64"
    } or key_record.get("algorithm") != "Ed25519":
        raise ProviderFencingReconciliationError("trusted Provider key record is malformed")
    public_key_bytes = _decode_base64(
        key_record.get("public_key_base64"), "trusted public key"
    )
    signature_bytes = _decode_base64(
        signature_record.get("value_base64"), "Provider signature"
    )
    if len(public_key_bytes) != 32 or len(signature_bytes) != 64:
        raise ProviderFencingReconciliationError("Ed25519 key or signature length is invalid")

    evidence = envelope.get("evidence")
    signed_payload = SIGNATURE_DOMAIN + _canonical(evidence)
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
            signature_bytes, signed_payload
        )
    except (InvalidSignature, ValueError) as exc:
        raise ProviderFencingReconciliationError(
            "Provider evidence signature verification failed"
        ) from exc

    result = validate_provider_fencing_reconciliation(
        candidate,
        evidence,
        now_unix=now_unix,
        maximum_age_seconds=maximum_age_seconds,
    )
    result["format"] = "ch17-provider-fencing-signed-reconciliation-result-v1"
    result["evidence_signature_verified"] = True
    result["signature_algorithm"] = "Ed25519"
    result["signer_key_id"] = key_id
    result["trust_store_sha256"] = hashlib.sha256(_canonical(trust_store)).hexdigest()
    result["limitations"] = [
        "The trust store is caller-supplied; its provenance, approval and protection must be independently established.",
        "A valid signature authenticates the signed snapshot only; it does not prove continuous Provider freeze or prevent post-sample mutation.",
        "This result is not production cutover approval, application-access authorization or permission to perform Provider operations.",
        "Replay prevention requires an independently durable evidence-id/nonce ledger and is not provided by this offline verifier.",
    ]
    # Deliberately retain both authorization flags as false.
    result["application_activation_authorized"] = False
    result["provider_operations_authorized"] = False
    return result

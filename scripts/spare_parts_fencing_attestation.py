"""Versioned fencing attestations: legacy HMAC and asymmetric Ed25519.

The Ed25519 signer protocol accepts a callback so a remote KMS/HSM adapter can
supply signatures without exposing a private key to the Coordinator process.
This module does not connect to any cloud KMS.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from typing import Any, Callable, Protocol


class FencingAttestationError(ValueError):
    """A fencing attestation is malformed, untrusted, mismatched or expired."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(value: str) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise FencingAttestationError("fencing attestation base64url component is invalid")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:
        raise FencingAttestationError("fencing attestation base64url component cannot be decoded") from exc


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


def _ed25519_signing_input(key_id: str, payload: str) -> bytes:
    return ("cnc-ch17-fencing-attestation.v2.ed25519." + key_id + "." + payload).encode("ascii")


class FencingAttestationSigner(Protocol):
    algorithm: str
    key_id: str

    def sign(self, signing_input: bytes) -> bytes: ...


class CallbackEd25519Signer:
    """KMS/HSM adapter seam: callback signs bytes, private key stays external."""

    algorithm = "ED25519"

    def __init__(self, *, key_id: str, signing_callback: Callable[[bytes], bytes]):
        if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id):
            raise FencingAttestationError("Ed25519 signing key ID is invalid")
        if not callable(signing_callback):
            raise FencingAttestationError("Ed25519 signing callback must be callable")
        self.key_id = key_id
        self._signing_callback = signing_callback

    def sign(self, signing_input: bytes) -> bytes:
        signature = self._signing_callback(signing_input)
        if not isinstance(signature, bytes) or len(signature) != 64:
            raise FencingAttestationError("Ed25519 signing callback must return a 64-byte signature")
        return signature


class Ed25519PrivateKeySigner(CallbackEd25519Signer):
    """Local test/reference signer; production should inject a KMS/HSM callback."""

    def __init__(self, *, key_id: str, private_key: Any):
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            if isinstance(private_key, bytes):
                if len(private_key) == 32:
                    key = Ed25519PrivateKey.from_private_bytes(private_key)
                elif private_key.startswith(b"-----BEGIN"):
                    key = serialization.load_pem_private_key(private_key, password=None)
                else:
                    raise FencingAttestationError("Ed25519 private key must be raw 32-byte seed or PEM")
            else:
                key = private_key
            if not isinstance(key, Ed25519PrivateKey):
                raise FencingAttestationError("configured private key is not Ed25519")
        except FencingAttestationError:
            raise
        except Exception as exc:
            raise FencingAttestationError("cannot load Ed25519 private key") from exc
        self._private_key = key
        super().__init__(key_id=key_id, signing_callback=key.sign)

    def public_key_raw(self) -> bytes:
        from cryptography.hazmat.primitives import serialization
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )


def create_fencing_attestation(
    claims: dict[str, Any], *, key_id: str, secret: str | bytes
) -> str:
    """Create legacy v1 HMAC proof for compatibility/migration only."""
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id):
        raise FencingAttestationError("fencing attestation key ID is invalid")
    payload = _b64url(canonical_claims(claims))
    signing_input = ("cnc-ch17-fencing-attestation.v1." + key_id + "." + payload).encode("ascii")
    signature = hmac.new(_key_bytes(secret), signing_input, hashlib.sha256).digest()
    return "v1." + key_id + "." + payload + "." + _b64url(signature)


def create_fencing_attestation_ed25519(
    claims: dict[str, Any], *, signer: FencingAttestationSigner
) -> str:
    """Create a v2 Ed25519 proof using a local key or injected KMS/HSM callback."""
    if getattr(signer, "algorithm", None) != "ED25519":
        raise FencingAttestationError("fencing proof signer must use ED25519")
    key_id = getattr(signer, "key_id", None)
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", key_id):
        raise FencingAttestationError("Ed25519 signer key ID is invalid")
    if claims.get("v") != 2 or claims.get("alg") != "ED25519" or claims.get("kid") != key_id:
        raise FencingAttestationError("Ed25519 claims must bind v2, algorithm and signer key ID")
    payload = _b64url(canonical_claims(claims))
    signature = signer.sign(_ed25519_signing_input(key_id, payload))
    if not isinstance(signature, bytes) or len(signature) != 64:
        raise FencingAttestationError("Ed25519 signer returned an invalid signature")
    return "v2.ed25519." + key_id + "." + payload + "." + _b64url(signature)


def _load_ed25519_public_key(value: Any):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if isinstance(value, Ed25519PublicKey):
        return value
    if not isinstance(value, bytes):
        raise FencingAttestationError("trusted Ed25519 public key must be bytes or a key object")
    try:
        if len(value) == 32:
            return Ed25519PublicKey.from_public_bytes(value)
        if value.startswith(b"-----BEGIN"):
            key = serialization.load_pem_public_key(value)
            if isinstance(key, Ed25519PublicKey):
                return key
        raise FencingAttestationError("trusted Ed25519 public key must be raw 32-byte or PEM")
    except FencingAttestationError:
        raise
    except Exception as exc:
        raise FencingAttestationError("cannot load trusted Ed25519 public key") from exc


def verify_fencing_attestation_signature(
    token: str, *, trusted_keys: dict[str, str | bytes] | None = None,
    trusted_ed25519_public_keys: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    if not isinstance(token, str) or len(token) > 8192:
        raise FencingAttestationError("fencing attestation is missing or exceeds the size limit")
    parts = token.split(".")
    if len(parts) == 4 and parts[0] == "v1":
        _, key_id, payload, signature_text = parts
        secret = (trusted_keys or {}).get(key_id)
        if secret is None:
            raise FencingAttestationError("HMAC fencing attestation key ID is not configured")
        signing_input = ("cnc-ch17-fencing-attestation.v1." + key_id + "." + payload).encode("ascii")
        expected = hmac.new(_key_bytes(secret), signing_input, hashlib.sha256).digest()
        supplied = _unb64url(signature_text)
        if not hmac.compare_digest(expected, supplied):
            raise FencingAttestationError("fencing attestation signature is invalid")
        expected_version, algorithm = 1, "HMAC-SHA256"
    elif len(parts) == 5 and parts[0] == "v2" and parts[1] == "ed25519":
        _, _, key_id, payload, signature_text = parts
        public_key = (trusted_ed25519_public_keys or {}).get(key_id)
        if public_key is None:
            raise FencingAttestationError("Ed25519 fencing attestation key ID is not configured")
        try:
            _load_ed25519_public_key(public_key).verify(
                _unb64url(signature_text), _ed25519_signing_input(key_id, payload)
            )
        except FencingAttestationError:
            raise
        except Exception as exc:
            raise FencingAttestationError("Ed25519 fencing attestation signature is invalid") from exc
        expected_version, algorithm = 2, "ED25519"
    else:
        raise FencingAttestationError("fencing attestation version, algorithm or structure is invalid")
    try:
        claims = json.loads(_unb64url(payload).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FencingAttestationError("fencing attestation claims cannot be decoded") from exc
    if not isinstance(claims, dict):
        raise FencingAttestationError("fencing attestation claims must be a JSON object")
    if claims.get("v") != expected_version or claims.get("kid") != key_id:
        raise FencingAttestationError("fencing attestation claims version or key ID mismatch")
    if algorithm == "ED25519" and claims.get("alg") != algorithm:
        raise FencingAttestationError("fencing attestation algorithm claim mismatch")
    return claims, key_id

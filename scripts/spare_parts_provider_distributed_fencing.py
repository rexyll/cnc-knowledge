#!/usr/bin/env python3
"""Provider-neutral distributed fencing publication protocol.

This module is a deterministic reference model for a trusted Provider gateway
using a strongly consistent, per-control-object compare-and-swap primitive.
It contains no AWS, Azure, Google Cloud, network, credential, KMS or HSM client.
Large payloads are assumed to be uploaded immutably before the final control
object is conditionally replaced. Readers trust only the manifest pointer in
the control object.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable, Protocol

from scripts.spare_parts_fencing_attestation import (
    FencingAttestationError,
    verify_fencing_attestation_signature,
)


class DistributedFencingError(ValueError):
    """Distributed fencing contract or control-record failure."""


class DistributedFencingStaleTokenError(DistributedFencingError):
    """A token or operation sequence is older than the committed high-water."""


class DistributedFencingConflictError(DistributedFencingError):
    """A token, lease, sequence or idempotency key conflicts with committed state."""


class DistributedFencingOutcomeUnknownError(DistributedFencingError):
    """A prior outcome cannot be proven; the operation must not be repeated."""


class DistributedFencingUnavailableError(DistributedFencingError):
    """The control store is unavailable; the Provider must fail closed."""


class ConditionalWriteConflictError(DistributedFencingError):
    """The control-object generation changed before the conditional write."""


class ConditionalWriteOutcomeUnknownError(DistributedFencingError):
    """The store may have committed the CAS but its response was lost."""


class ConditionalControlStoreUnavailableError(DistributedFencingError):
    """The conditional control-object store cannot serve this operation."""


class ConditionalObjectControlStore(Protocol):
    """One-key linearizable read and conditional replacement contract.

    read_control must be strongly consistent for the same control key.
    compare_and_swap must atomically compare the current opaque etag/generation
    and replace exactly that one key. expected_etag=None means create-if-absent.
    No cross-object atomicity is implied.
    """

    def read_control(self, control_key: str) -> tuple[str | None, bytes | None]: ...

    def compare_and_swap(
        self, control_key: str, *, expected_etag: str | None, payload: bytes
    ) -> str: ...


@dataclass(frozen=True)
class DistributedFencedCommitReceipt:
    scope: str
    fencing_token: int
    operation_sequence: int
    idempotency_key: str
    manifest_key: str
    manifest_sha256: str
    replayed: bool


def _safe_scope(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 512
        or value.startswith("/")
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or any(ord(ch) < 32 for ch in value)
    ):
        raise DistributedFencingError("fencing scope is invalid")
    return value


def _safe_manifest_key(scope: str, token: int, value: str) -> str:
    prefix = f"{scope}/staging/{token}/"
    if not isinstance(value, str) or not value.startswith(prefix):
        raise DistributedFencingError("manifest must be under the token-specific immutable staging prefix")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise DistributedFencingError("manifest object key is unsafe")
    if len(value) > 1024:
        raise DistributedFencingError("manifest object key is too long")
    return value


class InMemoryConditionalObjectControlStore:
    """Single-process CAS model for tests only; not a remote or multi-host store."""

    def __init__(self):
        self._lock = threading.Lock()
        self._objects: dict[str, tuple[str, bytes]] = {}
        self._revision = 0
        self._unavailable = False
        self._lose_response_once = False
        self.before_compare_and_swap: Callable[[str, str | None, bytes], None] | None = None

    def set_available(self, available: bool) -> None:
        with self._lock:
            self._unavailable = not bool(available)

    def lose_next_response_after_commit(self) -> None:
        with self._lock:
            self._lose_response_once = True

    def read_control(self, control_key: str) -> tuple[str | None, bytes | None]:
        with self._lock:
            if self._unavailable:
                raise ConditionalControlStoreUnavailableError("control store is unavailable")
            current = self._objects.get(control_key)
            return (None, None) if current is None else (current[0], bytes(current[1]))

    def compare_and_swap(
        self, control_key: str, *, expected_etag: str | None, payload: bytes
    ) -> str:
        hook = self.before_compare_and_swap
        if hook is not None:
            hook(control_key, expected_etag, payload)
        with self._lock:
            if self._unavailable:
                raise ConditionalControlStoreUnavailableError("control store is unavailable")
            current = self._objects.get(control_key)
            current_etag = None if current is None else current[0]
            if current_etag != expected_etag:
                raise ConditionalWriteConflictError("control-object ETag/generation precondition failed")
            self._revision += 1
            new_etag = f"mem-{self._revision}"
            self._objects[control_key] = (new_etag, bytes(payload))
            if self._lose_response_once:
                self._lose_response_once = False
                raise ConditionalWriteOutcomeUnknownError("CAS committed but the response was lost")
            return new_etag


class DistributedObjectFencingControlPlane:
    """Reference control-record state machine over a per-scope CAS object.

    The caller must upload and verify immutable payload objects first. This
    class atomically publishes only the manifest pointer and receipt inside the
    one per-scope control object. It assumes the Provider gateway verifies the
    Coordinator's Ed25519 proof and has exclusive write authority over control
    objects; direct client writes to those keys must be denied by IAM/policy.
    """

    SCHEMA_VERSION = 1
    DEFAULT_RECEIPT_HISTORY = 128

    def __init__(
        self,
        store: ConditionalObjectControlStore,
        *,
        trusted_ed25519_public_keys: dict[str, Any],
        trusted_issuers: set[str],
        clock_fn: Callable[[], float] = time.time,
        maximum_future_skew_seconds: float = 5.0,
        max_cas_attempts: int = 16,
        receipt_history: int = DEFAULT_RECEIPT_HISTORY,
    ):
        if not callable(getattr(store, "read_control", None)) or not callable(
            getattr(store, "compare_and_swap", None)
        ):
            raise DistributedFencingError("control store must implement read_control and compare_and_swap")
        if not isinstance(trusted_ed25519_public_keys, dict) or not trusted_ed25519_public_keys:
            raise DistributedFencingError("remote fencing profile requires trusted Ed25519 public keys")
        if not isinstance(trusted_issuers, set) or not trusted_issuers or any(
            not isinstance(value, str) or not value.strip() for value in trusted_issuers
        ):
            raise DistributedFencingError("remote fencing profile requires trusted issuer IDs")
        if (
            not isinstance(maximum_future_skew_seconds, (int, float))
            or isinstance(maximum_future_skew_seconds, bool)
            or not math.isfinite(maximum_future_skew_seconds)
            or maximum_future_skew_seconds < 0
        ):
            raise DistributedFencingError("maximum future clock skew must be finite and non-negative")
        if not isinstance(max_cas_attempts, int) or isinstance(max_cas_attempts, bool) or max_cas_attempts < 1:
            raise DistributedFencingError("maximum CAS attempts must be a positive integer")
        if not isinstance(receipt_history, int) or isinstance(receipt_history, bool) or receipt_history < 1:
            raise DistributedFencingError("receipt history must be a positive integer")
        self.store = store
        self.trusted_ed25519_public_keys = dict(trusted_ed25519_public_keys)
        self.trusted_issuers = set(trusted_issuers)
        self.clock_fn = clock_fn
        self.maximum_future_skew_seconds = float(maximum_future_skew_seconds)
        self.max_cas_attempts = max_cas_attempts
        self.receipt_history = receipt_history

    @staticmethod
    def _default_record(scope: str) -> dict[str, Any]:
        return {
            "schema_version": DistributedObjectFencingControlPlane.SCHEMA_VERSION,
            "scope": scope,
            "high_water_token": 0,
            "lease_state": "IDLE",
            "lease_id": None,
            "tenant_id": None,
            "owner_id": None,
            "lease_expires_at": None,
            "activation_idempotency_key": None,
            "revocation_idempotency_key": None,
            "latest_operation_sequence": 0,
            "recent_receipts": [],
            "current_commit": None,
        }

    def _read(self, scope: str) -> tuple[str | None, dict[str, Any]]:
        try:
            etag, raw = self.store.read_control(scope)
        except Exception as exc:
            raise DistributedFencingUnavailableError("strongly consistent control-object read failed closed") from exc
        if etag is None and raw is None:
            return None, self._default_record(scope)
        if not isinstance(etag, str) or not etag or not isinstance(raw, bytes):
            raise DistributedFencingError("control store returned an invalid etag or payload")
        try:
            record = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise DistributedFencingError("control object is not valid UTF-8 JSON") from exc
        self._validate_record(scope, record)
        return etag, record

    def _validate_record(self, scope: str, record: Any) -> None:
        expected = set(self._default_record(scope))
        if not isinstance(record, dict) or set(record) != expected:
            raise DistributedFencingError("control object schema is unknown or incomplete")
        if record.get("schema_version") != self.SCHEMA_VERSION or record.get("scope") != scope:
            raise DistributedFencingError("control object schema version or scope does not match")
        token = record.get("high_water_token")
        sequence = record.get("latest_operation_sequence")
        if (
            not isinstance(token, int) or isinstance(token, bool) or token < 0
            or not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0
        ):
            raise DistributedFencingError("control object high-water values are invalid")
        if record.get("lease_state") not in {"IDLE", "ACTIVE", "REVOKED"}:
            raise DistributedFencingError("control object lease state is invalid")
        if not isinstance(record.get("recent_receipts"), list):
            raise DistributedFencingError("control object receipt history is invalid")
        if record["lease_state"] == "ACTIVE":
            for name in ("lease_id", "tenant_id", "owner_id", "lease_expires_at"):
                if record.get(name) is None:
                    raise DistributedFencingError("active control record is missing lease identity or expiry")
        if record["lease_state"] == "IDLE" and token != 0:
            raise DistributedFencingError("non-zero fencing high-water cannot return to IDLE")

    def _verify(self, proof: str, *, scope: str, operation: str) -> dict[str, Any]:
        try:
            claims, key_id = verify_fencing_attestation_signature(
                proof, trusted_ed25519_public_keys=self.trusted_ed25519_public_keys
            )
        except FencingAttestationError as exc:
            raise DistributedFencingError("Coordinator Ed25519 proof verification failed") from exc
        required = {
            "v", "alg", "iss", "kid", "lease_id", "owner_id", "tenant_id", "domain",
            "fencing_token", "issued_at", "expires_at", "lease_expires_at",
            "fencing_scope", "resource_key", "operation", "idempotency_key",
        }
        if not required.issubset(claims):
            raise DistributedFencingError("Coordinator proof is missing required claims")
        if (
            claims.get("v") != 2
            or claims.get("alg") != "ED25519"
            or claims.get("kid") != key_id
            or claims.get("iss") not in self.trusted_issuers
            or claims.get("operation") != operation
            or claims.get("fencing_scope") != scope
            or claims.get("resource_key") != scope
        ):
            raise DistributedFencingError("Coordinator proof issuer, algorithm, operation or scope binding is invalid")
        for name in ("lease_id", "owner_id", "tenant_id", "domain", "idempotency_key"):
            if not isinstance(claims.get(name), str) or not claims[name].strip():
                raise DistributedFencingError(f"Coordinator proof claim {name} is invalid")
        token = claims.get("fencing_token")
        if not isinstance(token, int) or isinstance(token, bool) or token < 1:
            raise DistributedFencingError("Coordinator proof fencing token must be a positive integer")
        now = self.clock_fn()
        for name in ("issued_at", "expires_at", "lease_expires_at"):
            value = claims.get(name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise DistributedFencingError(f"Coordinator proof claim {name} is not a finite timestamp")
        if (
            claims["issued_at"] > now + self.maximum_future_skew_seconds
            or claims["expires_at"] <= now
            or claims["lease_expires_at"] <= now
            or claims["expires_at"] > claims["lease_expires_at"]
        ):
            raise DistributedFencingError("Coordinator proof is expired, not yet valid or exceeds its lease expiry")
        return claims

    @staticmethod
    def _encode(record: dict[str, Any]) -> bytes:
        return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

    def _cas(self, scope: str, etag: str | None, record: dict[str, Any]) -> bool:
        try:
            self.store.compare_and_swap(scope, expected_etag=etag, payload=self._encode(record))
            return True
        except ConditionalWriteConflictError:
            return False
        except ConditionalWriteOutcomeUnknownError:
            # Caller rereads the strongly consistent control object and resolves by idempotency.
            return False
        except Exception as exc:
            raise DistributedFencingUnavailableError("conditional control-object write failed closed") from exc

    def activate_lease(self, scope: str, *, fencing_attestation: str) -> dict[str, Any]:
        scope = _safe_scope(scope)
        claims = self._verify(fencing_attestation, scope=scope, operation="fencing:activate")
        token = claims["fencing_token"]
        for _ in range(self.max_cas_attempts):
            etag, current = self._read(scope)
            high_water = current["high_water_token"]
            if token < high_water:
                raise DistributedFencingStaleTokenError("lease activation token is below the object-store high-water")
            if token == high_water:
                if (
                    current["lease_state"] == "ACTIVE"
                    and current["lease_id"] == claims["lease_id"]
                    and current["tenant_id"] == claims["tenant_id"]
                    and current["owner_id"] == claims["owner_id"]
                    and current["activation_idempotency_key"] == claims["idempotency_key"]
                ):
                    return {**current, "replayed": True}
                raise DistributedFencingConflictError("fencing token is already consumed by another lease or state")
            updated = dict(current)
            updated.update({
                "high_water_token": token,
                "lease_state": "ACTIVE",
                "lease_id": claims["lease_id"],
                "tenant_id": claims["tenant_id"],
                "owner_id": claims["owner_id"],
                "lease_expires_at": claims["lease_expires_at"],
                "activation_idempotency_key": claims["idempotency_key"],
                "revocation_idempotency_key": None,
            })
            if self._cas(scope, etag, updated):
                return {**updated, "replayed": False}
        raise DistributedFencingUnavailableError("lease activation CAS contention exceeded its bounded retry budget")

    def revoke_lease(self, scope: str, *, fencing_attestation: str) -> dict[str, Any]:
        scope = _safe_scope(scope)
        claims = self._verify(fencing_attestation, scope=scope, operation="fencing:revoke")
        token = claims["fencing_token"]
        for _ in range(self.max_cas_attempts):
            etag, current = self._read(scope)
            if token < current["high_water_token"]:
                raise DistributedFencingStaleTokenError("cannot revoke a superseded lease")
            if token != current["high_water_token"] or current["lease_id"] != claims["lease_id"]:
                raise DistributedFencingConflictError("revocation proof does not identify the active lease")
            if current["lease_state"] == "REVOKED":
                if current["revocation_idempotency_key"] == claims["idempotency_key"]:
                    return {**current, "replayed": True}
                raise DistributedFencingConflictError("lease is already revoked by another operation")
            if current["lease_state"] != "ACTIVE":
                raise DistributedFencingConflictError("only an active lease can be revoked")
            updated = dict(current)
            updated["lease_state"] = "REVOKED"
            updated["revocation_idempotency_key"] = claims["idempotency_key"]
            if self._cas(scope, etag, updated):
                return {**updated, "replayed": False}
        raise DistributedFencingUnavailableError("lease revocation CAS contention exceeded its bounded retry budget")

    def publish_commit(self, scope: str, *, fencing_attestation: str) -> DistributedFencedCommitReceipt:
        scope = _safe_scope(scope)
        claims = self._verify(fencing_attestation, scope=scope, operation="fencing:publish")
        sequence = claims.get("operation_sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise DistributedFencingError("publish proof operation_sequence must be a positive integer")
        manifest_key = _safe_manifest_key(scope, claims["fencing_token"], claims.get("manifest_key"))
        manifest_sha256 = claims.get("manifest_sha256")
        if not isinstance(manifest_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256):
            raise DistributedFencingError("publish proof manifest_sha256 must be a lowercase SHA-256 digest")
        idem = claims["idempotency_key"]
        token = claims["fencing_token"]
        operation_sha256 = hashlib.sha256(self._encode({
            "scope": scope, "token": token, "sequence": sequence,
            "idempotency_key": idem, "manifest_key": manifest_key,
            "manifest_sha256": manifest_sha256,
        })).hexdigest()
        for _ in range(self.max_cas_attempts):
            etag, current = self._read(scope)
            if sequence <= current["latest_operation_sequence"]:
                receipt = next((item for item in current["recent_receipts"] if item["operation_sequence"] == sequence), None)
                if receipt is not None:
                    if (
                        receipt["idempotency_key"] != idem
                        or receipt["operation_sha256"] != operation_sha256
                    ):
                        raise DistributedFencingConflictError("operation sequence or idempotency key was reused with different content")
                    return DistributedFencedCommitReceipt(
                        scope, token, sequence, idem, manifest_key, manifest_sha256, True
                    )
                if any(item["idempotency_key"] == idem for item in current["recent_receipts"]):
                    raise DistributedFencingConflictError("idempotency key was reused with another operation sequence")
                raise DistributedFencingOutcomeUnknownError(
                    "operation is older than the retained receipt window; refusing a blind replay"
                )
            if (
                current["lease_state"] != "ACTIVE"
                or current["high_water_token"] != token
                or current["lease_id"] != claims["lease_id"]
                or current["tenant_id"] != claims["tenant_id"]
                or current["owner_id"] != claims["owner_id"]
            ):
                raise DistributedFencingStaleTokenError("object-store control record no longer authorizes this lease")
            if self.clock_fn() >= float(current["lease_expires_at"]):
                raise DistributedFencingStaleTokenError("object-store control record lease has expired")
            receipt_record = {
                "operation_sequence": sequence,
                "fencing_token": token,
                "idempotency_key": idem,
                "operation_sha256": operation_sha256,
                "manifest_key": manifest_key,
                "manifest_sha256": manifest_sha256,
            }
            updated = dict(current)
            updated["latest_operation_sequence"] = sequence
            updated["recent_receipts"] = (current["recent_receipts"] + [receipt_record])[-self.receipt_history:]
            updated["current_commit"] = {
                "operation_sequence": sequence,
                "fencing_token": token,
                "lease_id": claims["lease_id"],
                "manifest_key": manifest_key,
                "manifest_sha256": manifest_sha256,
                "idempotency_key": idem,
            }
            if self._cas(scope, etag, updated):
                return DistributedFencedCommitReceipt(
                    scope, token, sequence, idem, manifest_key, manifest_sha256, False
                )
        raise DistributedFencingUnavailableError("manifest publication CAS contention exceeded its bounded retry budget")

    def snapshot(self, scope: str) -> dict[str, Any]:
        scope = _safe_scope(scope)
        _, record = self._read(scope)
        return json.loads(json.dumps(record, ensure_ascii=False))


def main() -> int:
    """The module intentionally has no production CLI or network side effects."""
    print("Distributed fencing reference model: no network or cloud-provider integration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

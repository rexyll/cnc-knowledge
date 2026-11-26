#!/usr/bin/env python3
"""Backend-neutral Admission lease authority built on CoordinatorAuthorityStore.

This is a lease-lifecycle reference component, not a replacement for the
existing SQLite admission scheduler. It owns durable request idempotency,
monotonic fencing tokens, lease create/renew/release and transaction guards.
Capacity limits and fair waiter scheduling remain in the legacy SQLite service
until they can be migrated together with lease state into one backend transaction.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from scripts.spare_parts_backup_storage_adapter import (
    ProviderAdmissionLease,
    ProviderTaskContext,
)
from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreConflictError,
    AuthorityStoreDelete,
    AuthorityStoreEntry,
    AuthorityStoreGet,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    AuthorityStoreTxnOperation,
    AuthorityStoreTxnResult,
    CoordinatorAuthorityStore,
)


class AdmissionLeaseAuthorityError(RuntimeError):
    """Base failure for the backend-neutral Admission lease authority."""


class AdmissionLeaseConflictError(AdmissionLeaseAuthorityError):
    """Lease identity, CAS or fencing state conflicts."""


class AdmissionLeaseFinalizedError(AdmissionLeaseAuthorityError):
    """A request ID was already finalized and cannot be reused."""


class AdmissionLeaseUnknownOutcomeError(AdmissionLeaseAuthorityError):
    """A write may have committed but could not yet be reconciled."""


@dataclass(frozen=True)
class AdmissionLeaseRecord:
    request_id: str
    lease: ProviderAdmissionLease
    state: str
    backend_lease_id: int


class StoreBackedAdmissionLeaseAuthority:
    """Persist Admission lease lifecycle through one KV/Txn/Lease backend.

    Each active lease record is attached to a backend TTL lease. A permanent
    request-id record acts as an idempotency tombstone and survives TTL expiry.
    Renew atomically moves the active record to a newly granted backend lease.
    Authority mutations can include active_lease_compares() in their own Txn,
    so release/renew and a protected write are ordered by the same store.
    """

    _PREFIX = b"/cnc/admission/v1/"
    _TOKEN_KEY = _PREFIX + b"meta/fencing-token"
    _MAX_CAS_ATTEMPTS = 64

    def __init__(
        self,
        store: CoordinatorAuthorityStore,
        *,
        clock_fn: Callable[[], float] = time.time,
    ):
        required = ("linearizable_get", "transact", "lease_grant", "lease_keepalive", "lease_revoke")
        if any(not callable(getattr(store, name, None)) for name in required):
            raise ValueError("Admission lease authority requires a complete CoordinatorAuthorityStore")
        if not callable(clock_fn):
            raise ValueError("clock_fn must be callable")
        self.store = store
        self.clock_fn = clock_fn

    @staticmethod
    def _text(value: Any, field: str, maximum: int = 256) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
            raise AdmissionLeaseAuthorityError(f"{field} must contain 1..{maximum} non-NUL characters")
        return value.strip()

    @staticmethod
    def _digest_key(value: str) -> bytes:
        return hashlib.sha256(value.encode("utf-8")).hexdigest().encode("ascii")

    @classmethod
    def _lease_key(cls, lease_id: str) -> bytes:
        return cls._PREFIX + b"leases/" + cls._digest_key(lease_id)

    @classmethod
    def _request_key(cls, request_id: str) -> bytes:
        return cls._PREFIX + b"requests/" + cls._digest_key(request_id)

    @staticmethod
    def _identity(
        request_id: str,
        owner_id: str,
        task: ProviderTaskContext,
        domain: str,
    ) -> dict[str, str]:
        if not isinstance(task, ProviderTaskContext):
            raise AdmissionLeaseAuthorityError("a ProviderTaskContext is required")
        return {
            "request_id": request_id,
            "owner_id": owner_id,
            "task_id": StoreBackedAdmissionLeaseAuthority._text(task.task_id, "task ID"),
            "tenant_id": StoreBackedAdmissionLeaseAuthority._text(task.tenant_id, "tenant ID"),
            "domain": domain,
        }

    @staticmethod
    def _encode(record: dict[str, Any]) -> bytes:
        try:
            return json.dumps(
                record, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise AdmissionLeaseAuthorityError("Admission lease record is not canonical JSON") from exc

    @staticmethod
    def _decode(entry: AuthorityStoreEntry | None) -> dict[str, Any] | None:
        if entry is None:
            return None
        try:
            value = json.loads(entry.value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdmissionLeaseAuthorityError("stored Admission lease record is malformed") from exc
        if not isinstance(value, dict):
            raise AdmissionLeaseAuthorityError("stored Admission lease record must be an object")
        required = {
            "request_id", "lease_id", "owner_id", "task_id", "tenant_id",
            "domain", "fencing_token", "expires_at", "state", "backend_lease_id",
        }
        if set(value) != required:
            raise AdmissionLeaseAuthorityError("stored Admission lease record schema mismatch")
        if (
            not isinstance(value["fencing_token"], int)
            or isinstance(value["fencing_token"], bool)
            or value["fencing_token"] < 1
            or not isinstance(value["backend_lease_id"], int)
            or isinstance(value["backend_lease_id"], bool)
            or value["backend_lease_id"] < 1
            or not isinstance(value["expires_at"], (int, float))
            or isinstance(value["expires_at"], bool)
            or not math.isfinite(float(value["expires_at"]))
            or value["state"] not in {"ACTIVE", "RELEASED", "EXPIRED"}
        ):
            raise AdmissionLeaseAuthorityError("stored Admission lease record has invalid fields")
        for field in ("request_id", "lease_id", "owner_id", "task_id", "tenant_id", "domain"):
            if not isinstance(value[field], str) or not value[field]:
                raise AdmissionLeaseAuthorityError(f"stored Admission lease {field} is invalid")
        return value

    @staticmethod
    def _public_lease(value: dict[str, Any]) -> ProviderAdmissionLease:
        return ProviderAdmissionLease(
            lease_id=value["lease_id"],
            owner_id=value["owner_id"],
            tenant_id=value["tenant_id"],
            domain=value["domain"],
            fencing_token=int(value["fencing_token"]),
            expires_at=float(value["expires_at"]),
        )

    @staticmethod
    def _matches_identity(value: dict[str, Any], identity: dict[str, str]) -> bool:
        return all(value.get(k) == v for k, v in identity.items())

    def _read_request(self, identity: dict[str, str]) -> ProviderAdmissionLease | None:
        request_entry, _ = self.store.linearizable_get(self._request_key(identity["request_id"]))
        request_value = self._decode(request_entry)
        if request_value is None:
            return None
        if not self._matches_identity(request_value, identity):
            raise AdmissionLeaseConflictError(
                "request ID is already bound to a different owner/task/tenant/domain"
            )
        now = float(self.clock_fn())
        if request_value["state"] != "ACTIVE" or float(request_value["expires_at"]) <= now:
            self._mark_expired_if_needed(request_value, request_entry)
            raise AdmissionLeaseFinalizedError(
                "request ID was released or expired; use a new logical request ID"
            )
        lease_entry, _ = self.store.linearizable_get(self._lease_key(request_value["lease_id"]))
        lease_value = self._decode(lease_entry)
        if (
            lease_value is None or lease_entry is None
            or lease_entry.value != request_entry.value
            or lease_value["state"] != "ACTIVE"
            or float(lease_value["expires_at"]) <= now
        ):
            self._mark_expired_if_needed(request_value, request_entry)
            raise AdmissionLeaseFinalizedError(
                "request ID no longer identifies an active Admission lease"
            )
        return self._public_lease(lease_value)

    def _mark_expired_if_needed(
        self,
        value: dict[str, Any],
        request_entry: AuthorityStoreEntry | None,
    ) -> None:
        if request_entry is None or value.get("state") != "ACTIVE":
            return
        lease_key = self._lease_key(value["lease_id"])
        lease_entry, _ = self.store.linearizable_get(lease_key)
        expired = dict(value)
        expired["state"] = "EXPIRED"
        compares = [
            AuthorityStoreCompare(request_entry.key, "VALUE", "EQUAL", request_entry.value)
        ]
        success: list[AuthorityStoreTxnOperation] = [
            AuthorityStoreDelete(lease_key),
            AuthorityStorePut(request_entry.key, self._encode(expired)),
        ]
        if lease_entry is not None:
            compares.append(
                AuthorityStoreCompare(lease_key, "VALUE", "EQUAL", lease_entry.value)
            )
        try:
            result = self.store.transact(compares, success)
            if result.succeeded:
                self._safe_revoke(int(value["backend_lease_id"]))
        except Exception:
            # Expiry is already enforced by the backend TTL or by the expires_at
            # check. Tombstone repair is best-effort and never grants authority.
            return

    def _safe_revoke(self, backend_lease_id: int) -> None:
        try:
            self.store.lease_revoke(backend_lease_id)
        except Exception:
            # The active key has already moved or been deleted transactionally.
            # A leaked backend lease has no authority-bearing key and expires by TTL.
            return

    def acquire(
        self,
        *,
        task: ProviderTaskContext,
        domain: str,
        owner_id: str,
        request_id: str,
        lease_ttl_seconds: float,
    ) -> ProviderAdmissionLease:
        request_id = self._text(request_id, "request ID")
        owner_id = self._text(owner_id, "owner ID")
        domain = self._text(domain, "Admission domain", 64)
        identity = self._identity(request_id, owner_id, task, domain)
        if (
            not isinstance(lease_ttl_seconds, (int, float))
            or isinstance(lease_ttl_seconds, bool)
            or not math.isfinite(lease_ttl_seconds)
            or lease_ttl_seconds < 1
        ):
            raise AdmissionLeaseAuthorityError("lease TTL must be finite and at least one second")
        existing = self._read_request(identity)
        if existing is not None:
            return existing

        request_key = self._request_key(request_id)
        for _ in range(self._MAX_CAS_ATTEMPTS):
            # A concurrent caller with the same request ID may have committed
            # while this caller was reading the global token counter.
            existing = self._read_request(identity)
            if existing is not None:
                return existing
            counter_entry, _ = self.store.linearizable_get(self._TOKEN_KEY)
            if counter_entry is None:
                current_token = 0
                counter_compare = AuthorityStoreCompare(
                    self._TOKEN_KEY, "VERSION", "EQUAL", 0
                )
            else:
                try:
                    current_token = int(counter_entry.value.decode("ascii"))
                except (UnicodeDecodeError, ValueError) as exc:
                    raise AdmissionLeaseAuthorityError("fencing token counter is malformed") from exc
                if current_token < 0:
                    raise AdmissionLeaseAuthorityError("fencing token counter cannot be negative")
                counter_compare = AuthorityStoreCompare(
                    self._TOKEN_KEY, "MOD", "EQUAL", counter_entry.mod_revision
                )
            token = current_token + 1
            lease_id = "store-lease-" + uuid.uuid4().hex
            # etcd Lease RPCs use whole seconds. Flooring is conservative: a key
            # may expire slightly before expires_at, never after the requested TTL.
            backend_ttl = int(math.floor(float(lease_ttl_seconds)))
            backend_lease = self.store.lease_grant(backend_ttl)
            now = float(self.clock_fn())
            value = {
                **identity,
                "lease_id": lease_id,
                "fencing_token": token,
                "expires_at": now + float(lease_ttl_seconds),
                "state": "ACTIVE",
                "backend_lease_id": backend_lease.lease_id,
            }
            encoded = self._encode(value)
            result: AuthorityStoreTxnResult | None = None
            try:
                result = self.store.transact(
                    [
                        counter_compare,
                        AuthorityStoreCompare(request_key, "VERSION", "EQUAL", 0),
                        AuthorityStoreCompare(self._lease_key(lease_id), "VERSION", "EQUAL", 0),
                    ],
                    [
                        AuthorityStorePut(self._TOKEN_KEY, str(token).encode("ascii")),
                        AuthorityStorePut(
                            self._lease_key(lease_id), encoded, backend_lease.lease_id
                        ),
                        AuthorityStorePut(request_key, encoded),
                    ],
                )
            except AuthorityStoreOutcomeUnknownError as exc:
                try:
                    recovered = self._read_request(identity)
                    if recovered is not None:
                        return recovered
                except (AdmissionLeaseConflictError, AdmissionLeaseFinalizedError):
                    raise
                except Exception:
                    pass
                raise AdmissionLeaseUnknownOutcomeError(
                    "Admission lease create outcome is unknown; retain the same request ID and reconcile"
                ) from exc
            except Exception:
                self._safe_revoke(backend_lease.lease_id)
                raise
            if result.succeeded:
                return self._public_lease(value)
            self._safe_revoke(backend_lease.lease_id)
            # If another writer won the request ID, return its lease only when
            # its canonical identity matches; otherwise fail with a conflict.
        raise AdmissionLeaseConflictError("fencing-token CAS contention exceeded its retry budget")

    def renew(
        self,
        lease: ProviderAdmissionLease,
        *,
        lease_ttl_seconds: float,
    ) -> ProviderAdmissionLease | None:
        if (
            not isinstance(lease_ttl_seconds, (int, float))
            or isinstance(lease_ttl_seconds, bool)
            or not math.isfinite(lease_ttl_seconds)
            or lease_ttl_seconds < 1
        ):
            raise AdmissionLeaseAuthorityError("lease TTL must be finite and at least one second")
        lease_key = self._lease_key(lease.lease_id)
        lease_entry, _ = self.store.linearizable_get(lease_key)
        old_value = self._decode(lease_entry)
        if (
            lease_entry is None or old_value is None or old_value["state"] != "ACTIVE"
            or self._public_lease(old_value) != lease
            or float(old_value["expires_at"]) <= float(self.clock_fn())
        ):
            return None
        request_key = self._request_key(old_value["request_id"])
        request_entry, _ = self.store.linearizable_get(request_key)
        if request_entry is None or request_entry.value != lease_entry.value:
            return None
        new_backend_lease = self.store.lease_grant(int(math.floor(float(lease_ttl_seconds))))
        renewed_value = dict(old_value)
        renewed_value["expires_at"] = float(self.clock_fn()) + float(lease_ttl_seconds)
        renewed_value["backend_lease_id"] = new_backend_lease.lease_id
        encoded = self._encode(renewed_value)
        try:
            result = self.store.transact(
                [
                    AuthorityStoreCompare(lease_key, "VALUE", "EQUAL", lease_entry.value),
                    AuthorityStoreCompare(request_key, "VALUE", "EQUAL", request_entry.value),
                ],
                [
                    AuthorityStorePut(lease_key, encoded, new_backend_lease.lease_id),
                    AuthorityStorePut(request_key, encoded),
                ],
            )
        except AuthorityStoreOutcomeUnknownError as exc:
            try:
                current_lease, _ = self.store.linearizable_get(lease_key)
                current_request, _ = self.store.linearizable_get(request_key)
                if (
                    current_lease is not None and current_request is not None
                    and current_lease.value == encoded == current_request.value
                    and current_lease.lease_id == new_backend_lease.lease_id
                ):
                    self._safe_revoke(int(old_value["backend_lease_id"]))
                    return self._public_lease(renewed_value)
            except Exception:
                pass
            raise AdmissionLeaseUnknownOutcomeError(
                "Admission lease renewal outcome is unknown; reconcile the same lease ID"
            ) from exc
        if not result.succeeded:
            self._safe_revoke(new_backend_lease.lease_id)
            return None
        self._safe_revoke(int(old_value["backend_lease_id"]))
        return self._public_lease(renewed_value)

    def release(self, lease: ProviderAdmissionLease) -> bool:
        lease_key = self._lease_key(lease.lease_id)
        lease_entry, _ = self.store.linearizable_get(lease_key)
        value = self._decode(lease_entry)
        if (
            lease_entry is None or value is None or value["state"] != "ACTIVE"
            or self._public_lease(value) != lease
        ):
            return False
        request_key = self._request_key(value["request_id"])
        request_entry, _ = self.store.linearizable_get(request_key)
        if request_entry is None or request_entry.value != lease_entry.value:
            return False
        released = dict(value)
        released["state"] = "RELEASED"
        try:
            result = self.store.transact(
                [
                    AuthorityStoreCompare(lease_key, "VALUE", "EQUAL", lease_entry.value),
                    AuthorityStoreCompare(request_key, "VALUE", "EQUAL", request_entry.value),
                ],
                [
                    AuthorityStoreDelete(lease_key),
                    AuthorityStorePut(request_key, self._encode(released)),
                ],
            )
        except AuthorityStoreOutcomeUnknownError as exc:
            current_request, _ = self.store.linearizable_get(request_key)
            current_value = self._decode(current_request)
            if current_value is not None and current_value["state"] == "RELEASED":
                self._safe_revoke(int(value["backend_lease_id"]))
                return True
            raise AdmissionLeaseUnknownOutcomeError(
                "Admission lease release outcome is unknown; reconcile the same lease ID"
            ) from exc
        if not result.succeeded:
            return False
        self._safe_revoke(int(value["backend_lease_id"]))
        return True

    def validate(self, lease: ProviderAdmissionLease) -> bool:
        try:
            return bool(self.active_lease_compares(lease))
        except AdmissionLeaseAuthorityError:
            return False

    def active_lease_compares(
        self,
        lease: ProviderAdmissionLease,
        *,
        minimum_remaining_seconds: float = 0.0,
    ) -> tuple[AuthorityStoreCompare, ...]:
        """Return exact-value predicates to include in the protected authority Txn.

        The backend's TTL lease removes the active key at expiry. Therefore a
        release/renew/expiry racing the protected operation causes its same-Txn
        Compare to fail rather than accepting a stale lease read.
        """
        if (
            not isinstance(minimum_remaining_seconds, (int, float))
            or isinstance(minimum_remaining_seconds, bool)
            or not math.isfinite(minimum_remaining_seconds)
            or minimum_remaining_seconds < 0
        ):
            raise AdmissionLeaseAuthorityError("minimum remaining lease time must be non-negative")
        lease_key = self._lease_key(lease.lease_id)
        lease_entry, _ = self.store.linearizable_get(lease_key)
        value = self._decode(lease_entry)
        if (
            lease_entry is None or value is None or value["state"] != "ACTIVE"
            or self._public_lease(value) != lease
            or float(value["expires_at"])
            <= float(self.clock_fn()) + float(minimum_remaining_seconds)
        ):
            raise AdmissionLeaseConflictError("Admission lease is not active or has insufficient remaining TTL")
        request_key = self._request_key(value["request_id"])
        request_entry, _ = self.store.linearizable_get(request_key)
        if request_entry is None or request_entry.value != lease_entry.value:
            raise AdmissionLeaseConflictError("Admission request index does not match the active lease")
        return (
            AuthorityStoreCompare(lease_key, "VALUE", "EQUAL", lease_entry.value),
            AuthorityStoreCompare(request_key, "VALUE", "EQUAL", request_entry.value),
        )

    def transact_with_active_lease(
        self,
        lease: ProviderAdmissionLease,
        success: Sequence[AuthorityStoreTxnOperation],
        *,
        compares: Sequence[AuthorityStoreCompare] = (),
        failure: Sequence[AuthorityStoreTxnOperation] = (),
        minimum_remaining_seconds: float = 0.0,
    ) -> AuthorityStoreTxnResult:
        """Execute a protected mutation in the same Txn as Admission lease checks."""
        guard = self.active_lease_compares(
            lease, minimum_remaining_seconds=minimum_remaining_seconds
        )
        return self.store.transact(tuple(compares) + guard, success, failure)

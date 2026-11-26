#!/usr/bin/env python3
"""Unified store-backed Provider Admission scheduler reference.

All scheduling authority is represented by one revisioned aggregate key plus
TTL-attached active lease keys and persistent request-id tombstones. This
single-key design intentionally serializes mutations across domains so queue
fairness, global/tenant quotas, fencing tokens and lease state cannot be
split across independently committed authorities. It is a correctness-first
reference, not a high-throughput distributed scheduler.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from typing import Any, Callable, Sequence

from scripts.spare_parts_backup_storage_adapter import (
    BackupStorageError,
    ProviderAdmissionIdempotencyConflictError,
    ProviderAdmissionLease,
    ProviderAdmissionQueueFullError,
    ProviderAdmissionRequestFinalizedError,
    ProviderBulkheadFullError,
    ProviderCoordinatorUnavailableError,
    ProviderTaskContext,
)
from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreDelete,
    AuthorityStoreEntry,
    AuthorityStoreGet,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    AuthorityStoreTxnOperation,
    AuthorityStoreTxnResult,
    CoordinatorAuthorityStore,
)


class UnifiedAdmissionStateError(RuntimeError):
    """The durable aggregate or its indexes are inconsistent."""


class StoreBackedProviderAdmissionCoordinator:
    """Backend-neutral queue, quota and Admission lease scheduler.

    A single scheduler aggregate serializes admission decisions across all
    domains. The aggregate contains global/tenant policy, active lease
    identities, bounded fair waiters, fencing/waiter sequences and metrics.
    Active lease keys are attached to native store TTL leases. Request ID
    records remain permanent idempotency/terminal indexes.

    This deliberately prioritizes atomic correctness over throughput. It does
    not claim multi-key prefix scans, horizontal sharding, production capacity,
    or external etcd cluster validation.
    """

    _PREFIX = b"/cnc/admission/unified/v2/"
    _STATE_KEY = _PREFIX + b"scheduler/state"
    _MAX_CAS_ATTEMPTS = 64

    def __init__(
        self,
        store: CoordinatorAuthorityStore,
        *,
        global_limits: dict[str, int] | None = None,
        tenant_limits: dict[str, dict[str, int]] | None = None,
        max_waiters: int = 256,
        aging_interval_seconds: float = 1.0,
        poll_interval_seconds: float = 0.02,
        clock_fn: Callable[[], float] = time.time,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        required = ("linearizable_get", "transact", "lease_grant", "lease_keepalive", "lease_revoke")
        if any(not callable(getattr(store, name, None)) for name in required):
            raise BackupStorageError("unified admission requires a complete CoordinatorAuthorityStore")
        defaults = {"read": 4, "write": 2, "multipart": 2, "inventory": 1}
        if global_limits is not None:
            if set(global_limits) - set(defaults) or any(
                not isinstance(v, int) or isinstance(v, bool) or v < 1
                for v in global_limits.values()
            ):
                raise BackupStorageError("global limits must be positive integers for known domains")
            defaults.update(global_limits)
        tenants = {tenant: dict(values) for tenant, values in (tenant_limits or {}).items()}
        for tenant, values in tenants.items():
            if not isinstance(tenant, str) or not tenant.strip():
                raise BackupStorageError("tenant limits require nonblank tenant IDs")
            if set(values) - set(defaults) or any(
                not isinstance(v, int) or isinstance(v, bool) or v < 1
                for v in values.values()
            ):
                raise BackupStorageError("tenant limits must be positive integers for known domains")
        if not isinstance(max_waiters, int) or isinstance(max_waiters, bool) or max_waiters < 0:
            raise BackupStorageError("maximum waiters must be a non-negative integer")
        if not isinstance(aging_interval_seconds, (int, float)) or isinstance(aging_interval_seconds, bool) or not math.isfinite(aging_interval_seconds) or aging_interval_seconds <= 0:
            raise BackupStorageError("aging interval must be finite and positive")
        if not isinstance(poll_interval_seconds, (int, float)) or isinstance(poll_interval_seconds, bool) or not math.isfinite(poll_interval_seconds) or poll_interval_seconds <= 0:
            raise BackupStorageError("poll interval must be finite and positive")
        if not callable(clock_fn) or not callable(monotonic_fn):
            raise BackupStorageError("clock functions must be callable")

        self.store = store
        self.global_limits = defaults
        self.tenant_limits = tenants
        self.max_waiters = max_waiters
        self.aging_interval_seconds = float(aging_interval_seconds)
        self.poll_interval_seconds = float(poll_interval_seconds)
        self.clock_fn = clock_fn
        self.monotonic_fn = monotonic_fn
        policy = {
            "global_limits": defaults,
            "tenant_limits": tenants,
            "max_waiters": max_waiters,
            "aging_interval_seconds": self.aging_interval_seconds,
        }
        self._policy_hash = hashlib.sha256(
            json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self._initialize()

    @staticmethod
    def _text(value: Any, field: str, maximum: int = 256) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
            raise BackupStorageError(f"{field} must contain 1..{maximum} non-NUL characters")
        return value.strip()

    @classmethod
    def _digest(cls, value: str) -> bytes:
        return hashlib.sha256(value.encode("utf-8")).hexdigest().encode("ascii")

    @classmethod
    def _lease_key(cls, lease_id: str) -> bytes:
        return cls._PREFIX + b"leases/" + cls._digest(lease_id)

    @classmethod
    def _request_key(cls, request_id: str) -> bytes:
        return cls._PREFIX + b"requests/" + cls._digest(request_id)

    @staticmethod
    def _encode(value: dict[str, Any]) -> bytes:
        try:
            return json.dumps(
                value, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise UnifiedAdmissionStateError("admission state is not canonical JSON") from exc

    @staticmethod
    def _decode(entry: AuthorityStoreEntry | None) -> dict[str, Any] | None:
        if entry is None:
            return None
        try:
            value = json.loads(entry.value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UnifiedAdmissionStateError("stored admission state is malformed") from exc
        if not isinstance(value, dict):
            raise UnifiedAdmissionStateError("stored admission state must be an object")
        return value

    @staticmethod
    def _initial_state(policy_hash: str, global_limits: dict[str, int],
                       tenant_limits: dict[str, dict[str, int]], max_waiters: int,
                       aging_interval_seconds: float) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "policy_hash": policy_hash,
            "global_limits": global_limits,
            "tenant_limits": tenant_limits,
            "max_waiters": max_waiters,
            "aging_interval_seconds": aging_interval_seconds,
            "next_fencing_token": 0,
            "next_waiter_sequence": 0,
            "active": {},
            "waiters": [],
            "coordinator": {
                "leader": None,
                "scopes": {},
                "operations": {},
            },
            "counters": {
                "issued_leases": 0,
                "expired_leases": 0,
                "released_leases": 0,
                "rejected_capacity": 0,
                "rejected_queue": 0,
            },
        }

    def _initialize(self) -> None:
        for _ in range(8):
            entry, _ = self.store.linearizable_get(self._STATE_KEY)
            if entry is not None:
                state = self._decode(entry)
                if state is None or state.get("schema_version") != 1:
                    raise UnifiedAdmissionStateError("unsupported unified admission state schema")
                if state.get("policy_hash") != self._policy_hash:
                    raise BackupStorageError("admission policy differs from the store-bound policy")
                self._validate_state(state)
                return
            initial = self._initial_state(
                self._policy_hash, self.global_limits, self.tenant_limits,
                self.max_waiters, self.aging_interval_seconds,
            )
            result = self.store.transact(
                [AuthorityStoreCompare(self._STATE_KEY, "VERSION", "EQUAL", 0)],
                [AuthorityStorePut(self._STATE_KEY, self._encode(initial))],
            )
            if result.succeeded:
                return
        raise UnifiedAdmissionStateError("could not initialize unified admission state")

    @staticmethod
    def _validate_state(state: dict[str, Any]) -> None:
        required = {
            "schema_version", "policy_hash", "global_limits", "tenant_limits",
            "max_waiters", "aging_interval_seconds", "next_fencing_token",
            "next_waiter_sequence", "active", "waiters", "coordinator", "counters",
        }
        if state.get("schema_version") != 2:
            raise UnifiedAdmissionStateError("unsupported unified admission state schema")
        if set(state) != required or not isinstance(state.get("active"), dict) or not isinstance(state.get("waiters"), list):
            raise UnifiedAdmissionStateError("unified admission state schema mismatch")
        coordinator = state.get("coordinator")
        if (
            not isinstance(coordinator, dict)
            or set(coordinator) != {"leader", "scopes", "operations"}
            or not isinstance(coordinator.get("scopes"), dict)
            or not isinstance(coordinator.get("operations"), dict)
        ):
            raise UnifiedAdmissionStateError("unified Coordinator authority state is malformed")
        if not isinstance(state.get("counters"), dict):
            raise UnifiedAdmissionStateError("unified admission counters are malformed")
        if not isinstance(state.get("next_fencing_token"), int) or state["next_fencing_token"] < 0:
            raise UnifiedAdmissionStateError("unified admission fencing counter is invalid")
        if not isinstance(state.get("next_waiter_sequence"), int) or state["next_waiter_sequence"] < 0:
            raise UnifiedAdmissionStateError("unified admission waiter sequence is invalid")

    @staticmethod
    def _identity(
        request_id: str, owner_id: str, task: ProviderTaskContext, domain: str
    ) -> dict[str, str]:
        if not isinstance(task, ProviderTaskContext):
            raise BackupStorageError("a ProviderTaskContext is required")
        if not isinstance(task.priority, int) or isinstance(task.priority, bool):
            raise BackupStorageError("task priority must be an integer")
        return {
            "request_id": request_id,
            "owner_id": owner_id,
            "task_id": StoreBackedProviderAdmissionCoordinator._text(task.task_id, "task ID"),
            "tenant_id": StoreBackedProviderAdmissionCoordinator._text(task.tenant_id, "tenant ID"),
            "domain": domain,
        }

    @staticmethod
    def _record_schema(value: dict[str, Any]) -> bool:
        required = {
            "request_id", "lease_id", "owner_id", "task_id", "tenant_id",
            "domain", "fencing_token", "expires_at", "state", "backend_lease_id",
        }
        return (
            set(value) == required
            and all(isinstance(value.get(k), str) and value[k] for k in (
                "request_id", "lease_id", "owner_id", "task_id", "tenant_id", "domain"
            ))
            and isinstance(value.get("fencing_token"), int)
            and not isinstance(value.get("fencing_token"), bool)
            and value["fencing_token"] > 0
            and isinstance(value.get("backend_lease_id"), int)
            and not isinstance(value.get("backend_lease_id"), bool)
            and value["backend_lease_id"] > 0
            and isinstance(value.get("expires_at"), (int, float))
            and not isinstance(value.get("expires_at"), bool)
            and math.isfinite(float(value["expires_at"]))
            and value.get("state") in {"ACTIVE", "RELEASED", "EXPIRED"}
        )

    @staticmethod
    def _public_lease(record: dict[str, Any]) -> ProviderAdmissionLease:
        return ProviderAdmissionLease(
            lease_id=record["lease_id"], owner_id=record["owner_id"],
            tenant_id=record["tenant_id"], domain=record["domain"],
            fencing_token=int(record["fencing_token"]),
            expires_at=float(record["expires_at"]),
        )

    def _load_prepared(
        self, now: float, _attempt: int = 0
    ) -> tuple[
        AuthorityStoreEntry, dict[str, Any], list[AuthorityStoreCompare],
        list[AuthorityStoreTxnOperation], list[int], dict[str, AuthorityStoreEntry]
    ]:
        state_entry, _ = self.store.linearizable_get(self._STATE_KEY)
        if state_entry is None:
            raise UnifiedAdmissionStateError("unified admission state is missing")
        state = self._decode(state_entry)
        if state is None:
            raise UnifiedAdmissionStateError("unified admission state is empty")
        self._validate_state(state)
        if state["policy_hash"] != self._policy_hash:
            raise BackupStorageError("admission policy differs from the store-bound policy")

        prepared = json.loads(json.dumps(state))
        compares = [AuthorityStoreCompare(
            self._STATE_KEY, "MOD", "EQUAL", state_entry.mod_revision
        )]
        operations: list[AuthorityStoreTxnOperation] = []
        expired_backend_ids: list[int] = []
        active_entries: dict[str, AuthorityStoreEntry] = {}
        for lease_id, record in list(prepared["active"].items()):
            if not isinstance(record, dict) or not self._record_schema(record) or record["lease_id"] != lease_id:
                raise UnifiedAdmissionStateError("active admission lease record is malformed")
            encoded = self._encode(record)
            lease_key = self._lease_key(lease_id)
            request_key = self._request_key(record["request_id"])
            lease_entry, _ = self.store.linearizable_get(lease_key)
            request_entry, _ = self.store.linearizable_get(request_key)
            if request_entry is None or request_entry.value != encoded:
                latest_state, _ = self.store.linearizable_get(self._STATE_KEY)
                if latest_state is not None and latest_state.mod_revision != state_entry.mod_revision and _attempt < 16:
                    return self._load_prepared(now, _attempt + 1)
                raise UnifiedAdmissionStateError("active lease and persistent request index diverged")
            if lease_entry is not None and lease_entry.value != encoded:
                latest_state, _ = self.store.linearizable_get(self._STATE_KEY)
                if latest_state is not None and latest_state.mod_revision != state_entry.mod_revision and _attempt < 16:
                    return self._load_prepared(now, _attempt + 1)
                raise UnifiedAdmissionStateError("active lease key value diverged from scheduler state")
            if lease_entry is None or float(record["expires_at"]) <= now:
                if lease_entry is None:
                    compares.append(AuthorityStoreCompare(lease_key, "VERSION", "EQUAL", 0))
                else:
                    compares.append(AuthorityStoreCompare(lease_key, "VALUE", "EQUAL", encoded))
                compares.append(AuthorityStoreCompare(request_key, "VALUE", "EQUAL", encoded))
                expired = dict(record)
                expired["state"] = "EXPIRED"
                prepared["active"].pop(lease_id, None)
                operations.append(AuthorityStoreDelete(lease_key))
                operations.append(AuthorityStorePut(request_key, self._encode(expired)))
                expired_backend_ids.append(int(record["backend_lease_id"]))
                prepared["counters"]["expired_leases"] += 1
            else:
                compares.append(AuthorityStoreCompare(lease_key, "VALUE", "EQUAL", encoded))
                compares.append(AuthorityStoreCompare(request_key, "VALUE", "EQUAL", encoded))
                active_entries[lease_id] = lease_entry

        keep_waiters = []
        for waiter in prepared["waiters"]:
            if (
                not isinstance(waiter, dict)
                or not isinstance(waiter.get("request_id"), str)
                or not isinstance(waiter.get("expires_at"), (int, float))
                or float(waiter["expires_at"]) <= now
            ):
                continue
            keep_waiters.append(waiter)
        if len(keep_waiters) != len(prepared["waiters"]):
            prepared["waiters"] = keep_waiters
        return state_entry, prepared, compares, operations, expired_backend_ids, active_entries

    def _commit_state(
        self,
        state_entry: AuthorityStoreEntry,
        compares: Sequence[AuthorityStoreCompare],
        state: dict[str, Any],
        operations: Sequence[AuthorityStoreTxnOperation],
    ) -> AuthorityStoreTxnResult:
        branch = list(operations) + [
            AuthorityStorePut(self._STATE_KEY, self._encode(state))
        ]
        return self.store.transact(compares, branch)

    def _revoke_backend_leases(self, lease_ids: Sequence[int]) -> None:
        for lease_id in lease_ids:
            try:
                self.store.lease_revoke(lease_id)
            except Exception:
                # The active key has already been removed transactionally. A
                # leftover native Lease has no authority-bearing key and expires.
                continue

    @staticmethod
    def _same_identity(record: dict[str, Any], identity: dict[str, str]) -> bool:
        return all(record.get(key) == value for key, value in identity.items())

    def _resolve_existing(
        self, identity: dict[str, str], state: dict[str, Any]
    ) -> ProviderAdmissionLease | None:
        request_key = self._request_key(identity["request_id"])
        request_entry, _ = self.store.linearizable_get(request_key)
        record = self._decode(request_entry)
        if record is None:
            return None
        if not self._record_schema(record):
            raise UnifiedAdmissionStateError("persistent request index is malformed")
        if not self._same_identity(record, identity):
            raise ProviderAdmissionIdempotencyConflictError(
                "request ID is bound to another owner/task/tenant/domain"
            )
        if record["state"] != "ACTIVE":
            raise ProviderAdmissionRequestFinalizedError(
                "request ID is RELEASED or EXPIRED; use a new logical request ID"
            )
        state_record = state["active"].get(record["lease_id"])
        if state_record is None:
            # The request Range may linearize after a concurrent acquire committed
            # while this caller still holds an older scheduler snapshot.
            latest_state_entry, _ = self.store.linearizable_get(self._STATE_KEY)
            latest_state = self._decode(latest_state_entry)
            state_record = None if latest_state is None else latest_state["active"].get(record["lease_id"])
        if state_record is None or self._encode(state_record) != request_entry.value:
            raise UnifiedAdmissionStateError("request index does not match scheduler active set")
        lease_entry, _ = self.store.linearizable_get(self._lease_key(record["lease_id"]))
        if lease_entry is None or lease_entry.value != request_entry.value:
            raise ProviderAdmissionRequestFinalizedError("request ID no longer has an active backend lease")
        if float(record["expires_at"]) <= float(self.clock_fn()):
            raise ProviderAdmissionRequestFinalizedError("request ID lease has expired")
        return self._public_lease(record)

    def _waiter_for(
        self, waiters: list[dict[str, Any]], identity: dict[str, str]
    ) -> dict[str, Any] | None:
        found = next((w for w in waiters if w.get("request_id") == identity["request_id"]), None)
        if found is not None:
            if any(found.get(k) != v for k, v in identity.items()):
                raise ProviderAdmissionIdempotencyConflictError(
                    "waiting request ID is bound to another owner/task/tenant/domain"
                )
        return found

    def _active_counts(self, active: dict[str, dict[str, Any]], domain: str) -> tuple[int, int, dict[str, int]]:
        domain_records = [r for r in active.values() if r["domain"] == domain]
        tenant_counts: dict[str, int] = {}
        for record in domain_records:
            tenant = record["tenant_id"]
            tenant_counts[tenant] = tenant_counts.get(tenant, 0) + 1
        return len(domain_records), tenant_counts.get("", 0), tenant_counts

    def _selected_waiter(self, waiters: list[dict[str, Any]], domain: str,
                         tenant_counts: dict[str, int], now: float) -> str | None:
        eligible = [
            w for w in waiters
            if w["domain"] == domain
            and tenant_counts.get(w["tenant_id"], 0) < self.tenant_limits.get(
                w["tenant_id"], {}
            ).get(domain, self.global_limits[domain])
        ]
        if not eligible:
            return None
        selected = max(
            eligible,
            key=lambda w: (
                int(w["priority"])
                + max(0.0, now - float(w["queued_at"])) / self.aging_interval_seconds,
                -int(w["sequence"]),
            ),
        )
        return selected["request_id"]

    def _finish_waiter(self, request_id: str, *, rejected: bool) -> None:
        for _ in range(self._MAX_CAS_ATTEMPTS):
            now = float(self.clock_fn())
            state_entry, state, compares, operations, expired_ids, _ = self._load_prepared(now)
            old_len = len(state["waiters"])
            state["waiters"] = [w for w in state["waiters"] if w["request_id"] != request_id]
            if rejected:
                state["counters"]["rejected_capacity"] += 1
            changed = old_len != len(state["waiters"]) or bool(operations)
            if not changed:
                return
            result = self._commit_state(state_entry, compares, state, operations)
            if result.succeeded:
                self._revoke_backend_leases(expired_ids)
                return
        raise UnifiedAdmissionStateError("could not remove stale Admission waiter after CAS contention")

    def acquire(
        self,
        *,
        task: ProviderTaskContext,
        domain: str,
        owner_id: str,
        lease_ttl_seconds: float,
        timeout_seconds: float,
        check_task: Callable[[ProviderTaskContext], None],
        request_id: str | None = None,
    ) -> ProviderAdmissionLease:
        if request_id is None:
            request_id = uuid.uuid4().hex
        request_id = self._text(request_id, "request ID")
        owner_id = self._text(owner_id, "owner ID")
        domain = self._text(domain, "Admission domain", 64)
        if domain not in self.global_limits:
            raise BackupStorageError("unknown Admission domain")
        if not callable(check_task):
            raise BackupStorageError("check_task callback is required")
        if not isinstance(lease_ttl_seconds, (int, float)) or isinstance(lease_ttl_seconds, bool) or not math.isfinite(lease_ttl_seconds) or lease_ttl_seconds < 1:
            raise BackupStorageError("lease TTL must be finite and at least one second")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds < 0:
            raise BackupStorageError("acquire timeout must be finite and non-negative")
        identity = self._identity(request_id, owner_id, task, domain)
        start = float(self.monotonic_fn())
        deadline = start + float(timeout_seconds)
        wall_deadline = float(self.clock_fn()) + float(timeout_seconds)
        registered = False
        try:
            for _ in range(self._MAX_CAS_ATTEMPTS * max(1, int(timeout_seconds / self.poll_interval_seconds) + 1)):
                check_task(task)
                now = float(self.clock_fn())
                state_entry, state, compares, cleanup_ops, expired_ids, _ = self._load_prepared(now)

                try:
                    existing = self._resolve_existing(identity, state)
                except ProviderAdmissionRequestFinalizedError:
                    if cleanup_ops or state != self._decode(state_entry):
                        cleanup_result = self._commit_state(
                            state_entry, compares, state, cleanup_ops
                        )
                        if not cleanup_result.succeeded:
                            continue
                        self._revoke_backend_leases(expired_ids)
                    raise
                if existing is not None:
                    # If preparation pruned unrelated expired leases, persist
                    # that cleanup before returning an idempotent replay.
                    if cleanup_ops or state != self._decode(state_entry):
                        result = self._commit_state(state_entry, compares, state, cleanup_ops)
                        if not result.succeeded:
                            continue
                        self._revoke_backend_leases(expired_ids)
                    return existing

                waiter = self._waiter_for(state["waiters"], identity)
                if waiter is None:
                    candidate = {
                        **identity,
                        "priority": int(task.priority),
                        "sequence": state["next_waiter_sequence"] + 1,
                        "queued_at": now,
                        "expires_at": wall_deadline,
                    }
                else:
                    candidate = waiter
                test_waiters = list(state["waiters"])
                if waiter is None:
                    test_waiters.append(candidate)

                active_count, _, tenant_counts = self._active_counts(state["active"], domain)
                selected = self._selected_waiter(test_waiters, domain, tenant_counts, now)
                can_admit = (
                    active_count < self.global_limits[domain]
                    and tenant_counts.get(task.tenant_id, 0)
                    < self.tenant_limits.get(task.tenant_id, {}).get(
                        domain, self.global_limits[domain]
                    )
                    and selected == request_id
                )

                if can_admit:
                    backend_ttl = int(math.floor(float(lease_ttl_seconds)))
                    backend_lease = self.store.lease_grant(backend_ttl)
                    lease_id = "unified-lease-" + uuid.uuid4().hex
                    expires_at = float(self.clock_fn()) + float(backend_ttl)
                    token = int(state["next_fencing_token"]) + 1
                    record = {
                        **identity,
                        "lease_id": lease_id,
                        "fencing_token": token,
                        "expires_at": expires_at,
                        "state": "ACTIVE",
                        "backend_lease_id": backend_lease.lease_id,
                    }
                    state["next_fencing_token"] = token
                    state["active"][lease_id] = record
                    state["waiters"] = [
                        w for w in test_waiters if w["request_id"] != request_id
                    ]
                    state["counters"]["issued_leases"] += 1
                    request_key, lease_key = self._request_key(request_id), self._lease_key(lease_id)
                    attempt_compares = list(compares) + [
                        AuthorityStoreCompare(request_key, "VERSION", "EQUAL", 0),
                        AuthorityStoreCompare(lease_key, "VERSION", "EQUAL", 0),
                    ]
                    attempt_ops = list(cleanup_ops) + [
                        AuthorityStorePut(lease_key, self._encode(record), backend_lease.lease_id),
                        AuthorityStorePut(request_key, self._encode(record)),
                        AuthorityStorePut(self._STATE_KEY, self._encode(state)),
                    ]
                    try:
                        result = self.store.transact(attempt_compares, attempt_ops)
                    except AuthorityStoreOutcomeUnknownError as exc:
                        try:
                            latest, _ = self.store.linearizable_get(request_key)
                            found = self._decode(latest)
                            if (
                                found is not None and found.get("state") == "ACTIVE"
                                and self._same_identity(found, identity)
                            ):
                                latest_lease, _ = self.store.linearizable_get(
                                    self._lease_key(found["lease_id"])
                                )
                                latest_state_entry, _ = self.store.linearizable_get(self._STATE_KEY)
                                latest_state = self._decode(latest_state_entry)
                                if (
                                    latest_lease is not None and latest_lease.value == latest.value
                                    and latest_state is not None
                                    and latest_state["active"].get(found["lease_id"]) == found
                                ):
                                    self._revoke_backend_leases(expired_ids)
                                    return self._public_lease(found)
                        except Exception:
                            pass
                        # The acquire Txn may have committed despite the lost
                        # response. Keep its candidate Lease alive until TTL so
                        # a later retry with the same request ID can reconcile it.
                        self._revoke_backend_leases(expired_ids)
                        raise ProviderCoordinatorUnavailableError(
                            "Admission acquire outcome is unknown; reconcile using the same request ID",
                            phase="acquire", reservation_outcome_unknown=True,
                            request_id=request_id,
                        ) from exc
                    except Exception:
                        self._revoke_backend_leases([backend_lease.lease_id])
                        raise
                    if result.succeeded:
                        self._revoke_backend_leases(expired_ids)
                        return self._public_lease(record)
                    self._revoke_backend_leases([backend_lease.lease_id] + expired_ids)
                    continue

                if timeout_seconds <= 0 or float(self.monotonic_fn()) >= deadline:
                    if waiter is not None:
                        state["waiters"] = [
                            w for w in state["waiters"] if w["request_id"] != request_id
                        ]
                        registered = False
                    state["counters"]["rejected_capacity"] += 1
                    if cleanup_ops or state != self._decode(state_entry):
                        result = self._commit_state(state_entry, compares, state, cleanup_ops)
                        if not result.succeeded:
                            continue
                        self._revoke_backend_leases(expired_ids)
                    if not waiter and len(test_waiters) > self.max_waiters:
                        raise ProviderAdmissionQueueFullError(
                            "unified Admission queue is full", scope="store_backed"
                        )
                    raise ProviderBulkheadFullError(
                        f"shared {domain} concurrency or tenant quota is full"
                    )

                if waiter is None:
                    if len(state["waiters"]) >= self.max_waiters:
                        state["counters"]["rejected_queue"] += 1
                        if cleanup_ops or state != self._decode(state_entry):
                            result = self._commit_state(state_entry, compares, state, cleanup_ops)
                            if result.succeeded:
                                self._revoke_backend_leases(expired_ids)
                        raise ProviderAdmissionQueueFullError(
                            "unified Admission waiting queue is full", scope="store_backed"
                        )
                    state["next_waiter_sequence"] += 1
                    state["waiters"] = test_waiters
                    registered = True
                    self._commit_waiter_state(
                        state_entry, compares, state, cleanup_ops, expired_ids
                    )
                elif cleanup_ops or state != self._decode(state_entry):
                    self._commit_waiter_state(
                        state_entry, compares, state, cleanup_ops, expired_ids
                    )
                remaining = deadline - float(self.monotonic_fn())
                if remaining <= 0:
                    continue
                time.sleep(min(self.poll_interval_seconds, remaining))
            raise ProviderBulkheadFullError(
                f"shared {domain} admission retry budget was exhausted"
            )
        finally:
            if registered:
                self._finish_waiter(request_id, rejected=False)

    def _commit_waiter_state(
        self,
        entry: AuthorityStoreEntry,
        compares: Sequence[AuthorityStoreCompare],
        state: dict[str, Any],
        cleanup_ops: Sequence[AuthorityStoreTxnOperation],
        expired_ids: Sequence[int],
    ) -> None:
        result = self._commit_state(entry, compares, state, cleanup_ops)
        if result.succeeded:
            self._revoke_backend_leases(expired_ids)

    def _read_exact_active(
        self, lease: ProviderAdmissionLease
    ) -> tuple[AuthorityStoreEntry, AuthorityStoreEntry, AuthorityStoreEntry,
               dict[str, Any], AuthorityStoreEntry, dict[str, Any]]:
        state_entry, _ = self.store.linearizable_get(self._STATE_KEY)
        state = self._decode(state_entry)
        if state_entry is None or state is None:
            raise UnifiedAdmissionStateError("unified admission state is missing")
        record = state["active"].get(lease.lease_id)
        if record is None or not self._record_schema(record) or self._public_lease(record) != lease:
            raise ProviderBulkheadFullError("Admission lease is stale or not active")
        lease_entry, _ = self.store.linearizable_get(self._lease_key(lease.lease_id))
        request_entry, _ = self.store.linearizable_get(self._request_key(record["request_id"]))
        encoded = self._encode(record)
        if (
            lease_entry is None or request_entry is None
            or lease_entry.value != encoded or request_entry.value != encoded
            or float(record["expires_at"]) <= float(self.clock_fn())
        ):
            raise ProviderBulkheadFullError("Admission lease is stale or expired")
        return state_entry, state, lease_entry, record, request_entry, record

    def renew(
        self, lease: ProviderAdmissionLease, *, lease_ttl_seconds: float
    ) -> ProviderAdmissionLease | None:
        if not isinstance(lease_ttl_seconds, (int, float)) or isinstance(lease_ttl_seconds, bool) or not math.isfinite(lease_ttl_seconds) or lease_ttl_seconds < 1:
            raise BackupStorageError("lease TTL must be finite and at least one second")
        for _ in range(self._MAX_CAS_ATTEMPTS):
            now = float(self.clock_fn())
            state_entry, state, compares, cleanup_ops, expired_ids, _ = self._load_prepared(now)
            record = state["active"].get(lease.lease_id)
            if record is None or self._public_lease(record) != lease:
                if cleanup_ops:
                    cleanup_result = self._commit_state(
                        state_entry, compares, state, cleanup_ops
                    )
                    if not cleanup_result.succeeded:
                        continue
                    self._revoke_backend_leases(expired_ids)
                return None
            encoded = self._encode(record)
            lease_entry, _ = self.store.linearizable_get(self._lease_key(lease.lease_id))
            request_entry, _ = self.store.linearizable_get(self._request_key(record["request_id"]))
            if lease_entry is None or request_entry is None or lease_entry.value != encoded or request_entry.value != encoded:
                return None
            new_backend = self.store.lease_grant(int(math.floor(float(lease_ttl_seconds))))
            renewed = dict(record)
            renewed["expires_at"] = float(self.clock_fn()) + float(math.floor(float(lease_ttl_seconds)))
            renewed["backend_lease_id"] = new_backend.lease_id
            state["active"][lease.lease_id] = renewed
            ops = list(cleanup_ops) + [
                AuthorityStorePut(
                    self._lease_key(lease.lease_id), self._encode(renewed), new_backend.lease_id
                ),
                AuthorityStorePut(
                    self._request_key(record["request_id"]), self._encode(renewed)
                ),
                AuthorityStorePut(self._STATE_KEY, self._encode(state)),
            ]
            try:
                result = self.store.transact(
                    list(compares) + [
                        AuthorityStoreCompare(self._lease_key(lease.lease_id), "VALUE", "EQUAL", encoded),
                        AuthorityStoreCompare(self._request_key(record["request_id"]), "VALUE", "EQUAL", encoded),
                    ],
                    ops,
                )
            except AuthorityStoreOutcomeUnknownError as exc:
                current_lease, _ = self.store.linearizable_get(self._lease_key(lease.lease_id))
                current_request, _ = self.store.linearizable_get(self._request_key(record["request_id"]))
                if current_lease is not None and current_request is not None and current_lease.value == current_request.value == self._encode(renewed) and current_lease.lease_id == new_backend.lease_id:
                    self._revoke_backend_leases([int(record["backend_lease_id"])] + expired_ids)
                    return self._public_lease(renewed)
                # Preserve both native Lease candidates while the transaction
                # outcome is unknown. Any unattached Lease expires by TTL.
                self._revoke_backend_leases(expired_ids)
                raise ProviderCoordinatorUnavailableError(
                    "Admission renewal outcome is unknown; reconcile the same lease ID",
                    phase="renew", outcome_unknown=True,
                ) from exc
            if result.succeeded:
                self._revoke_backend_leases([int(record["backend_lease_id"])] + expired_ids)
                return self._public_lease(renewed)
            self._revoke_backend_leases([new_backend.lease_id] + expired_ids)
        return None

    def release(self, lease: ProviderAdmissionLease) -> bool:
        for _ in range(self._MAX_CAS_ATTEMPTS):
            now = float(self.clock_fn())
            state_entry, state, compares, cleanup_ops, expired_ids, _ = self._load_prepared(now)
            record = state["active"].get(lease.lease_id)
            if record is None or self._public_lease(record) != lease:
                if cleanup_ops:
                    cleanup_result = self._commit_state(
                        state_entry, compares, state, cleanup_ops
                    )
                    if not cleanup_result.succeeded:
                        continue
                    self._revoke_backend_leases(expired_ids)
                return False
            encoded = self._encode(record)
            released = dict(record)
            released["state"] = "RELEASED"
            state["active"].pop(lease.lease_id, None)
            state["counters"]["released_leases"] += 1
            ops = list(cleanup_ops) + [
                AuthorityStoreDelete(self._lease_key(lease.lease_id)),
                AuthorityStorePut(self._request_key(record["request_id"]), self._encode(released)),
                AuthorityStorePut(self._STATE_KEY, self._encode(state)),
            ]
            try:
                result = self.store.transact(
                    list(compares) + [
                        AuthorityStoreCompare(self._lease_key(lease.lease_id), "VALUE", "EQUAL", encoded),
                        AuthorityStoreCompare(self._request_key(record["request_id"]), "VALUE", "EQUAL", encoded),
                    ],
                    ops,
                )
            except AuthorityStoreOutcomeUnknownError as exc:
                current, _ = self.store.linearizable_get(self._request_key(record["request_id"]))
                value = self._decode(current)
                if value is not None and value.get("state") == "RELEASED":
                    self._revoke_backend_leases([int(record["backend_lease_id"])] + expired_ids)
                    return True
                raise ProviderCoordinatorUnavailableError(
                    "Admission release outcome is unknown; reconcile the same lease ID",
                    phase="release", outcome_unknown=True,
                ) from exc
            if result.succeeded:
                self._revoke_backend_leases([int(record["backend_lease_id"])] + expired_ids)
                return True
        return False

    def validate(self, lease: ProviderAdmissionLease) -> bool:
        try:
            self._read_exact_active(lease)
            return True
        except (ProviderBulkheadFullError, UnifiedAdmissionStateError):
            return False

    def active_lease_compares(
        self, lease: ProviderAdmissionLease, *, minimum_remaining_seconds: float = 0.0
    ) -> tuple[AuthorityStoreCompare, ...]:
        if not isinstance(minimum_remaining_seconds, (int, float)) or isinstance(minimum_remaining_seconds, bool) or not math.isfinite(minimum_remaining_seconds) or minimum_remaining_seconds < 0:
            raise BackupStorageError("minimum remaining lease time must be finite and non-negative")
        state_entry, state, lease_entry, record, request_entry, _ = self._read_exact_active(lease)
        if float(record["expires_at"]) <= float(self.clock_fn()) + float(minimum_remaining_seconds):
            raise ProviderBulkheadFullError("Admission lease has insufficient remaining TTL")
        return (
            AuthorityStoreCompare(self._lease_key(lease.lease_id), "VALUE", "EQUAL", lease_entry.value),
            AuthorityStoreCompare(self._request_key(record["request_id"]), "VALUE", "EQUAL", request_entry.value),
        )

    def transact_with_active_lease(
        self, lease: ProviderAdmissionLease,
        success: Sequence[AuthorityStoreTxnOperation], *,
        compares: Sequence[AuthorityStoreCompare] = (),
        failure: Sequence[AuthorityStoreTxnOperation] = (),
        minimum_remaining_seconds: float = 0.0,
    ) -> AuthorityStoreTxnResult:
        guard = self.active_lease_compares(
            lease, minimum_remaining_seconds=minimum_remaining_seconds
        )
        return self.store.transact(tuple(compares) + guard, success, failure)

    def reclaim_expired(self) -> int:
        for _ in range(self._MAX_CAS_ATTEMPTS):
            now = float(self.clock_fn())
            before_entry, _ = self.store.linearizable_get(self._STATE_KEY)
            if before_entry is None:
                raise UnifiedAdmissionStateError("unified admission state is missing")
            state = self._decode(before_entry)
            if state is None:
                raise UnifiedAdmissionStateError("unified admission state is malformed")
            before_active = len(state["active"])
            entry, prepared, compares, operations, expired_ids, _ = self._load_prepared(now)
            if not operations and prepared == self._decode(entry):
                return 0
            expired_count = before_active - len(prepared["active"])
            result = self._commit_state(entry, compares, prepared, operations)
            if not result.succeeded:
                continue
            self._revoke_backend_leases(expired_ids)
            return max(expired_count, 0)
        raise UnifiedAdmissionStateError("could not reclaim expired Admission state")

    def snapshot(self) -> dict[str, Any]:
        self.reclaim_expired()
        entry, _ = self.store.linearizable_get(self._STATE_KEY)
        state = self._decode(entry)
        if state is None:
            raise UnifiedAdmissionStateError("unified admission state is missing")
        active_counts: dict[str, int] = {}
        tenant_counts: dict[str, int] = {}
        for value in state["active"].values():
            domain, tenant = value["domain"], value["tenant_id"]
            active_counts[domain] = active_counts.get(domain, 0) + 1
            key = f"{tenant}:{domain}"
            tenant_counts[key] = tenant_counts.get(key, 0) + 1
        return {
            "policy_hash": state["policy_hash"],
            "active_by_domain": active_counts,
            "active_by_tenant_domain": tenant_counts,
            "queue_depth": len(state["waiters"]),
            "next_fencing_token": state["next_fencing_token"],
            "counters": dict(state["counters"]),
        }

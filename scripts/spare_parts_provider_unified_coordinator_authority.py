#!/usr/bin/env python3
"""Coordinator Leader, scope fencing and operation ledger on unified Admission state.

The Coordinator data is nested in StoreBackedProviderAdmissionCoordinator's
single revisioned aggregate. Every mutation compares that aggregate revision,
the live Leader TTL key and (where supplied) the exact Admission lease/request
records in the same CoordinatorAuthorityStore transaction.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any, Callable, Sequence

from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreDelete,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
    AuthorityStoreTxnOperation,
)
from scripts.spare_parts_provider_coordinator_authority import (
    CoordinatorAuthorityConflictError,
    CoordinatorAuthorityError,
    CoordinatorAuthorityStaleLeaderError,
    CoordinatorAuthorityUnavailableError,
    CoordinatorLeadershipLease,
    DurableAuthorityOperation,
    _digest,
    _lease_values,
    _required_text,
    _scope,
    _sha256,
    _tenant_scope,
)
from scripts.spare_parts_provider_unified_admission_store import (
    StoreBackedProviderAdmissionCoordinator,
    UnifiedAdmissionStateError,
)


class StoreBackedCoordinatorAuthority:
    """Unified store-backed Coordinator durable authority.

    Leader TTL, tenant scope fencing state and the ACTIVATE/REVOKE/PUBLISH
    operation ledger share the Admission scheduler's aggregate state and KV
    transaction boundary. This is a reference implementation; the single
    aggregate remains a global serialization point.
    """

    _LEADER_KEY = (
        StoreBackedProviderAdmissionCoordinator._PREFIX
        + b"coordinator/leader"
    )
    _PENDING_STATES = (
        "PENDING_ACTIVATION", "REVOKING", "PENDING_PUBLISH", "RECOVERY_REVIEW"
    )
    _OP_STATES = {
        "PENDING_ACTIVATION", "ACTIVE", "REVOKING", "REVOKED",
        "PENDING_PUBLISH", "COMMITTED", "RECOVERY_REVIEW",
    }
    _SCOPE_STATES = {
        "IDLE", "PENDING_ACTIVATION", "ACTIVE", "REVOKING", "REVOKED",
        "FENCED", "RECOVERY_REQUIRED",
    }
    _MAX_CAS_ATTEMPTS = 64

    def __init__(
        self,
        scheduler: StoreBackedProviderAdmissionCoordinator,
        *,
        clock_fn: Callable[[], float] | None = None,
    ):
        if not isinstance(scheduler, StoreBackedProviderAdmissionCoordinator):
            raise CoordinatorAuthorityError(
                "a StoreBackedProviderAdmissionCoordinator is required"
            )
        self.scheduler = scheduler
        self.store = scheduler.store
        self.clock_fn = clock_fn or scheduler.clock_fn
        if not callable(self.clock_fn):
            raise CoordinatorAuthorityError("Coordinator clock must be callable")
        self._initialize_coordinator_state()

    @staticmethod
    def _initial_coordinator_state() -> dict[str, Any]:
        return {"leader": None, "scopes": {}, "operations": {}}

    def _initialize_coordinator_state(self) -> None:
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, _ = self.scheduler._load_prepared(
                float(self.clock_fn())
            )
            coordinator = state.get("coordinator")
            if not isinstance(coordinator, dict):
                raise UnifiedAdmissionStateError("Coordinator aggregate is missing")
            required = {"leader", "scopes", "operations"}
            if set(coordinator) != required:
                raise UnifiedAdmissionStateError("Coordinator aggregate schema mismatch")
            if not isinstance(coordinator["scopes"], dict) or not isinstance(coordinator["operations"], dict):
                raise UnifiedAdmissionStateError("Coordinator scope/operation indexes are malformed")
            if coordinator["leader"] is not None and not self._valid_leader_record(coordinator["leader"]):
                raise UnifiedAdmissionStateError("Coordinator Leader record is malformed")
            result = self.scheduler._commit_state(entry, compares, state, cleanup)
            if result.succeeded:
                self.scheduler._revoke_backend_leases(expired)
                return
        raise UnifiedAdmissionStateError("could not initialize Coordinator aggregate")

    @staticmethod
    def _valid_leader_record(record: Any) -> bool:
        return (
            isinstance(record, dict)
            and set(record) == {"leader_id", "epoch", "expires_at", "backend_lease_id"}
            and isinstance(record.get("leader_id"), str) and bool(record["leader_id"])
            and isinstance(record.get("epoch"), int) and not isinstance(record["epoch"], bool)
            and record["epoch"] > 0
            and isinstance(record.get("expires_at"), (int, float))
            and not isinstance(record["expires_at"], bool)
            and math.isfinite(float(record["expires_at"]))
            and isinstance(record.get("backend_lease_id"), int)
            and not isinstance(record["backend_lease_id"], bool)
            and record["backend_lease_id"] > 0
        )

    @staticmethod
    def _op_key(scope: str, idempotency_key: str) -> str:
        raw = (scope + "\x00" + idempotency_key).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _default_scope(scope: str, now: float) -> dict[str, Any]:
        return {
            "high_water_token": 0,
            "lease_id": None,
            "owner_id": None,
            "tenant_id": None,
            "domain": None,
            "lease_expires_at": None,
            "lease_state": "IDLE",
            "latest_operation_sequence": 0,
            "provider_generation": None,
            "updated_at": now,
        }

    @staticmethod
    def _operation_from_record(record: dict[str, Any]) -> DurableAuthorityOperation:
        return DurableAuthorityOperation(
            scope=record["scope"],
            kind=record["kind"],
            idempotency_key=record["idempotency_key"],
            request_sha256=record["request_sha256"],
            fencing_token=int(record["fencing_token"]),
            operation_sequence=(
                None if record["operation_sequence"] is None
                else int(record["operation_sequence"])
            ),
            lease_id=record["lease_id"],
            owner_id=record["owner_id"],
            tenant_id=record["tenant_id"],
            domain=record["domain"],
            lease_expires_at=float(record["lease_expires_at"]),
            state=record["state"],
            provider_generation=record["provider_generation"],
            manifest_key=record["manifest_key"],
            manifest_sha256=record["manifest_sha256"],
        )

    @staticmethod
    def _record_from_operation(
        *, scope: str, kind: str, idempotency_key: str, request_sha256: str,
        fencing_token: int, operation_sequence: int | None, lease_values: dict[str, Any],
        state: str, provider_generation: str | None, now: float,
        manifest_key: str | None = None, manifest_sha256: str | None = None,
    ) -> dict[str, Any]:
        return {
            "scope": scope,
            "kind": kind,
            "idempotency_key": idempotency_key,
            "request_sha256": request_sha256,
            "fencing_token": fencing_token,
            "operation_sequence": operation_sequence,
            "lease_id": lease_values["lease_id"],
            "owner_id": lease_values["owner_id"],
            "tenant_id": lease_values["tenant_id"],
            "domain": lease_values["domain"],
            "lease_expires_at": lease_values["lease_expires_at"],
            "state": state,
            "provider_generation": provider_generation,
            "manifest_key": manifest_key,
            "manifest_sha256": manifest_sha256,
            "created_at": now,
            "updated_at": now,
        }

    def _load(self):
        now = float(self.clock_fn())
        entry, state, compares, cleanup, expired, _ = self.scheduler._load_prepared(now)
        if "coordinator" not in state:
            raise UnifiedAdmissionStateError("Coordinator aggregate is missing")
        return entry, state, compares, cleanup, expired, now

    def _leader_guard(
        self, state: dict[str, Any], leadership: CoordinatorLeadershipLease, now: float
    ) -> tuple[AuthorityStoreCompare, dict[str, Any]]:
        if not isinstance(leadership, CoordinatorLeadershipLease):
            raise CoordinatorAuthorityStaleLeaderError(
                "a current Coordinator leadership lease is required"
            )
        record = state["coordinator"]["leader"]
        leader_entry, _ = self.store.linearizable_get(self._LEADER_KEY)
        if (
            not self._valid_leader_record(record)
            or leader_entry is None
            or leader_entry.value != self.scheduler._encode(record)
            or record["leader_id"] != leadership.leader_id
            or int(record["epoch"]) != leadership.epoch
            or float(record["expires_at"]) <= now
        ):
            raise CoordinatorAuthorityStaleLeaderError(
                "Coordinator Leader epoch is stale, expired or no longer authoritative"
            )
        return (
            AuthorityStoreCompare(self._LEADER_KEY, "VALUE", "EQUAL", leader_entry.value),
            record,
        )

    def _admission_values(
        self, state: dict[str, Any], lease: Any, now: float
    ) -> dict[str, Any]:
        values = _lease_values(lease)
        record = state["active"].get(values["lease_id"])
        if (
            not isinstance(record, dict)
            or record.get("state") != "ACTIVE"
            or record.get("owner_id") != values["owner_id"]
            or record.get("tenant_id") != values["tenant_id"]
            or record.get("domain") != values["domain"]
            or int(record.get("fencing_token", 0)) != values["admission_fencing_token"]
            or abs(float(record.get("expires_at", 0)) - values["lease_expires_at"]) > 1e-6
            or float(record.get("expires_at", 0)) <= now
        ):
            raise CoordinatorAuthorityConflictError(
                "admission lease is inactive, expired or mismatched"
            )
        return values

    def _commit(
        self, entry, state, compares, cleanup, expired, extra_compares=(), extra_operations=()
    ):
        result = self.scheduler._commit_state(
            entry,
            tuple(compares) + tuple(extra_compares),
            state,
            tuple(cleanup) + tuple(extra_operations),
        )
        if result.succeeded:
            self.scheduler._revoke_backend_leases(expired)
        return result

    def _commit_read(self, entry, state, compares, cleanup, expired, extra_compares):
        if cleanup or state != self.scheduler._decode(entry):
            return self._commit(entry, state, compares, cleanup, expired, extra_compares)
        result = self.store.transact(tuple(compares) + tuple(extra_compares), [])
        if result.succeeded:
            self.scheduler._revoke_backend_leases(expired)
        return result

    @staticmethod
    def _ensure_scope(scopes: dict[str, Any], scope: str, now: float) -> dict[str, Any]:
        current = scopes.get(scope)
        if current is None:
            current = StoreBackedCoordinatorAuthority._default_scope(scope, now)
            scopes[scope] = current
        if (
            not isinstance(current, dict)
            or set(current) != {
                "high_water_token", "lease_id", "owner_id", "tenant_id", "domain",
                "lease_expires_at", "lease_state", "latest_operation_sequence",
                "provider_generation", "updated_at",
            }
            or current.get("lease_state") not in StoreBackedCoordinatorAuthority._SCOPE_STATES
        ):
            raise UnifiedAdmissionStateError("Coordinator scope record is malformed")
        return current

    @staticmethod
    def _get_existing(
        operations: dict[str, Any], scope: str, idem: str, *,
        kind: str, request_sha256: str,
    ) -> DurableAuthorityOperation | None:
        record = operations.get(StoreBackedCoordinatorAuthority._op_key(scope, idem))
        if record is None:
            return None
        if (
            not isinstance(record, dict)
            or record.get("scope") != scope
            or record.get("idempotency_key") != idem
        ):
            raise UnifiedAdmissionStateError("Coordinator operation index is malformed")
        if record.get("kind") != kind or record.get("request_sha256") != request_sha256:
            raise CoordinatorAuthorityConflictError(
                "Coordinator idempotency key was reused for another operation or payload"
            )
        return StoreBackedCoordinatorAuthority._operation_from_record(record)

    @staticmethod
    def _put_operation(operations: dict[str, Any], record: dict[str, Any]) -> None:
        if record.get("state") not in StoreBackedCoordinatorAuthority._OP_STATES:
            raise UnifiedAdmissionStateError("Coordinator operation state is invalid")
        operations[StoreBackedCoordinatorAuthority._op_key(
            record["scope"], record["idempotency_key"]
        )] = record

    def claim_leadership(
        self,
        leader_id: str,
        *,
        ttl_seconds: float,
        recovery_epoch_floor: int | None = None,
        reconciliation_ref: str | None = None,
    ) -> CoordinatorLeadershipLease:
        leader_id = _required_text(leader_id, "leader ID", maximum=128)
        if (
            not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool)
            or not math.isfinite(ttl_seconds) or not 1 <= ttl_seconds <= 300
        ):
            raise CoordinatorAuthorityError("Leader TTL must be in [1, 300] seconds")
        ttl = int(math.floor(float(ttl_seconds)))
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            current = state["coordinator"]["leader"]
            current_epoch = 0 if current is None else int(current["epoch"])
            current_key, _ = self.store.linearizable_get(self._LEADER_KEY)
            if current_key is not None:
                raise CoordinatorAuthorityConflictError(
                    "another Coordinator Leader TTL lease is still present"
                )
            if recovery_epoch_floor is not None:
                if (
                    not isinstance(recovery_epoch_floor, int)
                    or isinstance(recovery_epoch_floor, bool)
                    or recovery_epoch_floor <= current_epoch
                ):
                    raise CoordinatorAuthorityError(
                        "external recovery epoch floor must exceed the restored epoch"
                    )
                _required_text(
                    reconciliation_ref, "external leadership reconciliation reference",
                    maximum=256,
                )
            epoch = max(current_epoch + 1, recovery_epoch_floor or 0)
            backend = self.store.lease_grant(ttl)
            # The backend may grant a TTL longer than requested (for example,
            # because of server-side minimums). Persist the granted TTL, not
            # the requested value, so the wall-clock expiry never leads the
            # native lease attached to the Leader key.
            record = {
                "leader_id": leader_id,
                "epoch": epoch,
                "expires_at": now + backend.ttl_seconds,
                "backend_lease_id": backend.lease_id,
            }
            state["coordinator"]["leader"] = record
            leader_value = self.scheduler._encode(record)
            ops = [AuthorityStorePut(self._LEADER_KEY, leader_value, backend.lease_id)]
            compares_all = tuple(compares) + (
                AuthorityStoreCompare(self._LEADER_KEY, "VERSION", "EQUAL", 0),
            )
            try:
                result = self.scheduler._commit_state(
                    entry, compares_all, state, tuple(cleanup) + tuple(ops)
                )
            except AuthorityStoreOutcomeUnknownError as exc:
                latest_key, _ = self.store.linearizable_get(self._LEADER_KEY)
                latest_state_entry, _ = self.store.linearizable_get(self.scheduler._STATE_KEY)
                latest_state = self.scheduler._decode(latest_state_entry)
                if (
                    latest_key is not None and latest_key.value == leader_value
                    and latest_state is not None
                    and latest_state["coordinator"]["leader"] == record
                ):
                    self.scheduler._revoke_backend_leases(expired)
                    return CoordinatorLeadershipLease(leader_id, epoch, float(record["expires_at"]))
                raise CoordinatorAuthorityUnavailableError(
                    "Coordinator leadership claim outcome is unknown"
                ) from exc
            if result.succeeded:
                self.scheduler._revoke_backend_leases(expired)
                return CoordinatorLeadershipLease(leader_id, epoch, float(record["expires_at"]))
            self.scheduler._revoke_backend_leases([backend.lease_id] + expired)
        raise CoordinatorAuthorityUnavailableError(
            "Coordinator leadership claim exhausted transaction retries"
        )

    def renew_leadership(
        self, leadership: CoordinatorLeadershipLease, *, ttl_seconds: float
    ) -> CoordinatorLeadershipLease:
        if (
            not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool)
            or not math.isfinite(ttl_seconds) or not 1 <= ttl_seconds <= 300
        ):
            raise CoordinatorAuthorityError("Leader TTL must be in [1, 300] seconds")
        ttl = int(math.floor(float(ttl_seconds)))
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            guard, current = self._leader_guard(state, leadership, now)
            old_backend_id = int(current["backend_lease_id"])
            backend = self.store.lease_grant(ttl)
            renewed = dict(current)
            renewed["expires_at"] = now + backend.ttl_seconds
            renewed["backend_lease_id"] = backend.lease_id
            value = self.scheduler._encode(renewed)
            state["coordinator"]["leader"] = renewed
            try:
                result = self.scheduler._commit_state(
                    entry, tuple(compares) + (guard,),
                    state,
                    tuple(cleanup) + (
                        AuthorityStorePut(self._LEADER_KEY, value, backend.lease_id),
                    ),
                )
            except AuthorityStoreOutcomeUnknownError as exc:
                key, _ = self.store.linearizable_get(self._LEADER_KEY)
                latest, _ = self.store.linearizable_get(self.scheduler._STATE_KEY)
                latest_state = self.scheduler._decode(latest)
                if (
                    key is not None and key.value == value
                    and latest_state is not None
                    and latest_state["coordinator"]["leader"] == renewed
                ):
                    self.scheduler._revoke_backend_leases([old_backend_id] + expired)
                    return CoordinatorLeadershipLease(
                        leadership.leader_id, leadership.epoch, float(renewed["expires_at"])
                    )
                # Keep the candidate TTL alive until expiry; the transaction
                # may have committed even if the response could not be read.
                self.scheduler._revoke_backend_leases(expired)
                raise CoordinatorAuthorityUnavailableError(
                    "Coordinator leadership renewal outcome is unknown"
                ) from exc
            if result.succeeded:
                self.scheduler._revoke_backend_leases([old_backend_id] + expired)
                return CoordinatorLeadershipLease(
                    leadership.leader_id, leadership.epoch, float(renewed["expires_at"])
                )
            self.scheduler._revoke_backend_leases([backend.lease_id] + expired)
        raise CoordinatorAuthorityUnavailableError(
            "Coordinator leadership renewal exhausted transaction retries"
        )

    def prepare_activation(
        self, leadership: CoordinatorLeadershipLease, lease: Any, *,
        scope: str, idempotency_key: str,
    ) -> DurableAuthorityOperation:
        scope = _scope(scope)
        idem = _required_text(idempotency_key, "activation idempotency key", maximum=256)
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            values = self._admission_values(state, lease, now)
            normalized_scope = _tenant_scope(scope, values["tenant_id"])
            digest = _digest({"scope": normalized_scope, "kind": "ACTIVATE", **values})
            existing = self._get_existing(
                state["coordinator"]["operations"], normalized_scope, idem,
                kind="ACTIVATE", request_sha256=digest,
            )
            if existing is not None:
                result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
                if result.succeeded:
                    return existing
                continue
            current = self._ensure_scope(
                state["coordinator"]["scopes"], normalized_scope, now
            )
            if current["lease_state"] in {"PENDING_ACTIVATION", "REVOKING"}:
                raise CoordinatorAuthorityConflictError(
                    "scope has an unresolved activation or revocation; reconcile it first"
                )
            token = int(current["high_water_token"]) + 1
            record = self._record_from_operation(
                scope=normalized_scope, kind="ACTIVATE", idempotency_key=idem,
                request_sha256=digest, fencing_token=token, operation_sequence=None,
                lease_values=values, state="PENDING_ACTIVATION",
                provider_generation=None, now=now,
            )
            self._put_operation(state["coordinator"]["operations"], record)
            current.update({
                "high_water_token": token,
                "lease_id": values["lease_id"],
                "owner_id": values["owner_id"],
                "tenant_id": values["tenant_id"],
                "domain": values["domain"],
                "lease_expires_at": values["lease_expires_at"],
                "lease_state": "PENDING_ACTIVATION",
                "provider_generation": None,
                "updated_at": now,
            })
            result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
            if result.succeeded:
                return self._operation_from_record(record)
        raise CoordinatorAuthorityUnavailableError("activation preparation exhausted transaction retries")

    def confirm_activation(
        self, leadership: CoordinatorLeadershipLease, *, scope: str,
        fencing_token: int, idempotency_key: str, observed_provider_state: str,
        observed_high_water_token: int, observed_lease_id: str, provider_generation: str,
    ) -> DurableAuthorityOperation:
        scope = _scope(scope)
        idem = _required_text(idempotency_key, "activation idempotency key", maximum=256)
        generation = _required_text(provider_generation, "Provider generation", maximum=256)
        lease_id = _required_text(observed_lease_id, "observed Provider lease ID", maximum=128)
        if observed_provider_state != "ACTIVE" or observed_high_water_token != fencing_token:
            raise CoordinatorAuthorityConflictError(
                "Provider read-back does not confirm the requested activation"
            )
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            op = state["coordinator"]["operations"].get(self._op_key(scope, idem))
            if (
                op is None or op["kind"] != "ACTIVATE"
                or int(op["fencing_token"]) != fencing_token or op["lease_id"] != lease_id
            ):
                raise CoordinatorAuthorityConflictError(
                    "activation confirmation does not match a durable request"
                )
            current = self._ensure_scope(state["coordinator"]["scopes"], scope, now)
            if int(current["high_water_token"]) != fencing_token or current["lease_id"] != lease_id:
                raise CoordinatorAuthorityStaleLeaderError(
                    "activation has been superseded by a newer scope token"
                )
            if op["state"] == "ACTIVE":
                if op["provider_generation"] != generation:
                    raise CoordinatorAuthorityConflictError(
                        "activation was already confirmed at another Provider generation"
                    )
                result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
                if result.succeeded:
                    return self._operation_from_record(op)
                continue
            if op["state"] not in {"PENDING_ACTIVATION", "RECOVERY_REVIEW"}:
                raise CoordinatorAuthorityConflictError(
                    "activation is not pending reconciliation"
                )
            op.update({"state": "ACTIVE", "provider_generation": generation, "updated_at": now})
            current.update({
                "lease_state": "ACTIVE", "provider_generation": generation,
                "updated_at": now,
            })
            result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
            if result.succeeded:
                return self._operation_from_record(op)
        raise CoordinatorAuthorityUnavailableError("activation confirmation exhausted transaction retries")

    def prepare_revocation(
        self, leadership: CoordinatorLeadershipLease, lease: Any, *,
        scope: str, fencing_token: int, idempotency_key: str,
    ) -> DurableAuthorityOperation:
        scope = _scope(scope)
        idem = _required_text(idempotency_key, "revocation idempotency key", maximum=256)
        if not isinstance(fencing_token, int) or isinstance(fencing_token, bool) or fencing_token < 1:
            raise CoordinatorAuthorityError("revocation fencing token must be a positive integer")
        digest = None
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            values = self._admission_values(state, lease, now)
            normalized_scope = _tenant_scope(scope, values["tenant_id"])
            digest = _digest({
                "scope": normalized_scope, "kind": "REVOKE", "fencing_token": fencing_token,
                "lease_id": values["lease_id"], "owner_id": values["owner_id"],
                "tenant_id": values["tenant_id"],
            })
            existing = self._get_existing(
                state["coordinator"]["operations"], normalized_scope, idem,
                kind="REVOKE", request_sha256=digest,
            )
            if existing is not None:
                result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
                if result.succeeded:
                    return existing
                continue
            current = self._ensure_scope(state["coordinator"]["scopes"], normalized_scope, now)
            if (
                current["lease_state"] != "ACTIVE"
                or int(current["high_water_token"]) != fencing_token
                or current["lease_id"] != values["lease_id"]
            ):
                raise CoordinatorAuthorityConflictError(
                    "only the exact active scope lease can enter REVOKING"
                )
            record = self._record_from_operation(
                scope=normalized_scope, kind="REVOKE", idempotency_key=idem,
                request_sha256=digest, fencing_token=fencing_token, operation_sequence=None,
                lease_values=values, state="REVOKING",
                provider_generation=None, now=now,
            )
            self._put_operation(state["coordinator"]["operations"], record)
            current.update({"lease_state": "REVOKING", "updated_at": now})
            result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
            if result.succeeded:
                return self._operation_from_record(record)
        raise CoordinatorAuthorityUnavailableError("revocation preparation exhausted transaction retries")

    def confirm_revocation(
        self, leadership: CoordinatorLeadershipLease, *, scope: str,
        fencing_token: int, idempotency_key: str, observed_provider_state: str,
        observed_high_water_token: int, observed_lease_id: str, provider_generation: str,
    ) -> DurableAuthorityOperation:
        scope = _scope(scope)
        idem = _required_text(idempotency_key, "revocation idempotency key", maximum=256)
        generation = _required_text(provider_generation, "Provider generation", maximum=256)
        lease_id = _required_text(observed_lease_id, "observed Provider lease ID", maximum=128)
        if observed_provider_state != "REVOKED" or observed_high_water_token != fencing_token:
            raise CoordinatorAuthorityConflictError(
                "Provider read-back does not confirm the requested revocation"
            )
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            op = state["coordinator"]["operations"].get(self._op_key(scope, idem))
            if (
                op is None or op["kind"] != "REVOKE"
                or int(op["fencing_token"]) != fencing_token or op["lease_id"] != lease_id
            ):
                raise CoordinatorAuthorityConflictError(
                    "revocation confirmation does not match a durable request"
                )
            current = self._ensure_scope(state["coordinator"]["scopes"], scope, now)
            if int(current["high_water_token"]) != fencing_token or current["lease_id"] != lease_id:
                raise CoordinatorAuthorityStaleLeaderError("revocation target has been superseded")
            if op["state"] == "REVOKED":
                if op["provider_generation"] != generation:
                    raise CoordinatorAuthorityConflictError(
                        "revocation was already confirmed at another Provider generation"
                    )
                result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
                if result.succeeded:
                    return self._operation_from_record(op)
                continue
            if op["state"] != "REVOKING":
                raise CoordinatorAuthorityConflictError("revocation is not pending reconciliation")
            op.update({"state": "REVOKED", "provider_generation": generation, "updated_at": now})
            current.update({
                "lease_state": "REVOKED", "provider_generation": generation,
                "updated_at": now,
            })
            result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
            if result.succeeded:
                return self._operation_from_record(op)
        raise CoordinatorAuthorityUnavailableError("revocation confirmation exhausted transaction retries")

    def allocate_operation_sequence(
        self, leadership: CoordinatorLeadershipLease, lease: Any, *,
        scope: str, idempotency_key: str, manifest_key: str, manifest_sha256: str,
    ) -> DurableAuthorityOperation:
        scope = _scope(scope)
        idem = _required_text(idempotency_key, "publish idempotency key", maximum=256)
        key = _required_text(manifest_key, "manifest key", maximum=1024)
        digest = _sha256(manifest_sha256, "manifest SHA-256")
        if not key.startswith(scope + "/") or any(part in {".", ".."} for part in key.split("/")) or "\\" in key:
            raise CoordinatorAuthorityError("manifest key must be a normalized key below the fencing scope")
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            values = _lease_values(lease)
            normalized_scope = _tenant_scope(scope, values["tenant_id"])
            request_sha = _digest({
                "scope": normalized_scope, "kind": "PUBLISH", "lease_id": values["lease_id"],
                "manifest_key": key, "manifest_sha256": digest,
            })
            existing = self._get_existing(
                state["coordinator"]["operations"], normalized_scope, idem,
                kind="PUBLISH", request_sha256=request_sha,
            )
            if existing is not None:
                result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
                if result.succeeded:
                    return existing
                continue
            values = self._admission_values(state, lease, now)
            current = self._ensure_scope(state["coordinator"]["scopes"], normalized_scope, now)
            if (
                current["lease_state"] != "ACTIVE"
                or current["lease_id"] != values["lease_id"]
                or current["owner_id"] != values["owner_id"]
                or current["tenant_id"] != values["tenant_id"]
                or int(current["high_water_token"]) < 1
                or float(current["lease_expires_at"] or 0) <= now
            ):
                raise CoordinatorAuthorityConflictError(
                    "publish requires the exact confirmed ACTIVE scope lease"
                )
            sequence = int(current["latest_operation_sequence"]) + 1
            token = int(current["high_water_token"])
            record = self._record_from_operation(
                scope=normalized_scope, kind="PUBLISH", idempotency_key=idem,
                request_sha256=request_sha, fencing_token=token,
                operation_sequence=sequence, lease_values=values,
                state="PENDING_PUBLISH", provider_generation=None, now=now,
                manifest_key=key, manifest_sha256=digest,
            )
            self._put_operation(state["coordinator"]["operations"], record)
            current.update({"latest_operation_sequence": sequence, "updated_at": now})
            result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
            if result.succeeded:
                return self._operation_from_record(record)
        raise CoordinatorAuthorityUnavailableError("publish sequence allocation exhausted transaction retries")

    def confirm_publish(
        self, leadership: CoordinatorLeadershipLease, *, scope: str,
        idempotency_key: str, observed_provider_state: str,
        observed_fencing_token: int, observed_operation_sequence: int,
        observed_idempotency_key: str, observed_manifest_key: str,
        observed_manifest_sha256: str, provider_generation: str,
    ) -> DurableAuthorityOperation:
        scope = _scope(scope)
        idem = _required_text(idempotency_key, "publish idempotency key", maximum=256)
        generation = _required_text(provider_generation, "Provider generation", maximum=256)
        if observed_provider_state != "ACTIVE" or observed_idempotency_key != idem:
            raise CoordinatorAuthorityConflictError(
                "Provider receipt does not identify the requested publish"
            )
        observed_key = _required_text(observed_manifest_key, "observed Provider manifest key", maximum=1024)
        observed_digest = _sha256(observed_manifest_sha256, "observed Provider manifest SHA-256")
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            op = state["coordinator"]["operations"].get(self._op_key(scope, idem))
            if op is None or op["kind"] != "PUBLISH":
                raise CoordinatorAuthorityConflictError(
                    "publish confirmation has no durable sequence allocation"
                )
            if (
                int(op["fencing_token"]) != observed_fencing_token
                or int(op["operation_sequence"]) != observed_operation_sequence
                or op["manifest_key"] != observed_key
                or op["manifest_sha256"] != observed_digest
            ):
                raise CoordinatorAuthorityConflictError(
                    "Provider receipt token/sequence/manifest differs from Coordinator allocation"
                )
            if op["state"] == "COMMITTED":
                if op["provider_generation"] != generation:
                    raise CoordinatorAuthorityConflictError(
                        "publish was already confirmed at another Provider generation"
                    )
                result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
                if result.succeeded:
                    return self._operation_from_record(op)
                continue
            current = self._ensure_scope(state["coordinator"]["scopes"], scope, now)
            if (
                current["lease_state"] != "ACTIVE"
                or int(current["high_water_token"]) != observed_fencing_token
                or current["lease_id"] != op["lease_id"]
            ):
                raise CoordinatorAuthorityStaleLeaderError(
                    "publish lease was superseded before confirmation"
                )
            if op["state"] != "PENDING_PUBLISH":
                raise CoordinatorAuthorityConflictError("publish is not pending reconciliation")
            op.update({"state": "COMMITTED", "provider_generation": generation, "updated_at": now})
            result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
            if result.succeeded:
                return self._operation_from_record(op)
        raise CoordinatorAuthorityUnavailableError("publish confirmation exhausted transaction retries")

    def authorize_operation_signing(
        self, leadership: CoordinatorLeadershipLease,
        operation: DurableAuthorityOperation,
    ) -> None:
        if not isinstance(operation, DurableAuthorityOperation):
            raise CoordinatorAuthorityError("a durable Coordinator operation is required")
        expected = {
            "ACTIVATE": "PENDING_ACTIVATION",
            "REVOKE": "REVOKING",
            "PUBLISH": "PENDING_PUBLISH",
        }.get(operation.kind)
        if expected is None:
            raise CoordinatorAuthorityError("unsupported distributed fencing operation kind")
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            row = state["coordinator"]["operations"].get(
                self._op_key(operation.scope, operation.idempotency_key)
            )
            if (
                row is None
                or row.get("kind") != operation.kind
                or row.get("request_sha256") != operation.request_sha256
                or int(row.get("fencing_token", -1)) != operation.fencing_token
                or row.get("lease_id") != operation.lease_id
                or row.get("owner_id") != operation.owner_id
                or row.get("tenant_id") != operation.tenant_id
                or row.get("domain") != operation.domain
                or abs(float(row.get("lease_expires_at", 0)) - operation.lease_expires_at) > 1e-6
                or row.get("state") != expected
                or row.get("operation_sequence") != operation.operation_sequence
                or row.get("manifest_key") != operation.manifest_key
                or row.get("manifest_sha256") != operation.manifest_sha256
            ):
                raise CoordinatorAuthorityStaleLeaderError(
                    "operation is not pending in the durable Coordinator state"
                )
            result = self._commit_read(
                entry, state, compares, cleanup, expired, (leader_guard,)
            )
            if result.succeeded:
                return
        raise CoordinatorAuthorityUnavailableError(
            "operation signing authorization exhausted transaction retries"
        )

    def list_pending_operations(
        self, leadership: CoordinatorLeadershipLease, *, scope: str | None = None
    ) -> list[DurableAuthorityOperation]:
        if scope is not None:
            scope = _scope(scope)
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            rows = [
                record for record in state["coordinator"]["operations"].values()
                if record["state"] in self._PENDING_STATES
                and (scope is None or record["scope"] == scope)
            ]
            rows.sort(key=lambda r: (
                float(r["created_at"]), r["scope"],
                -1 if r["operation_sequence"] is None else int(r["operation_sequence"]),
            ))
            result = self._commit_read(
                entry, state, compares, cleanup, expired, (leader_guard,)
            )
            if result.succeeded:
                return [self._operation_from_record(r) for r in rows]
        raise CoordinatorAuthorityUnavailableError(
            "pending operation listing exhausted transaction retries"
        )

    def reconcile_after_restore(
        self, leadership: CoordinatorLeadershipLease, *, scope: str,
        external_high_water_token: int, external_operation_sequence: int,
        reconciliation_ref: str,
    ) -> dict[str, Any]:
        scope = _scope(scope)
        _required_text(reconciliation_ref, "external fencing reconciliation reference", maximum=256)
        for value, name in (
            (external_high_water_token, "external high-water token"),
            (external_operation_sequence, "external operation sequence"),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CoordinatorAuthorityError(f"{name} must be a non-negative integer")
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader_guard, _ = self._leader_guard(state, leadership, now)
            current = self._ensure_scope(state["coordinator"]["scopes"], scope, now)
            if external_high_water_token < int(current["high_water_token"]):
                raise CoordinatorAuthorityConflictError(
                    "external Provider token floor is below the restored Coordinator value"
                )
            if external_operation_sequence < int(current["latest_operation_sequence"]):
                raise CoordinatorAuthorityConflictError(
                    "external Provider sequence floor is below the restored Coordinator value"
                )
            for operation in state["coordinator"]["operations"].values():
                if (
                    operation["scope"] == scope
                    and operation["state"] in {
                        "PENDING_ACTIVATION", "REVOKING", "PENDING_PUBLISH"
                    }
                ):
                    operation.update({"state": "RECOVERY_REVIEW", "updated_at": now})
            current.update({
                "high_water_token": external_high_water_token,
                "latest_operation_sequence": external_operation_sequence,
                "lease_id": None,
                "owner_id": None,
                "tenant_id": None,
                "domain": None,
                "lease_expires_at": None,
                "lease_state": "RECOVERY_REQUIRED",
                "provider_generation": None,
                "updated_at": now,
            })
            result = self._commit(entry, state, compares, cleanup, expired, (leader_guard,))
            if result.succeeded:
                return {
                    "scope": scope,
                    "high_water_token": external_high_water_token,
                    "latest_operation_sequence": external_operation_sequence,
                    "lease_state": "RECOVERY_REQUIRED",
                    "reconciliation_ref": reconciliation_ref,
                    "automatic_cutover": False,
                }
        raise CoordinatorAuthorityUnavailableError(
            "restore reconciliation exhausted transaction retries"
        )

    def snapshot(self, scope: str) -> dict[str, Any]:
        scope = _scope(scope)
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            current = state["coordinator"]["scopes"].get(scope)
            if current is None:
                current = self._default_scope(scope, now)
            else:
                current = dict(current)
            result = self._commit_read(entry, state, compares, cleanup, expired, ())
            if result.succeeded:
                return {"scope": scope, **current}
        raise CoordinatorAuthorityUnavailableError("Coordinator snapshot exhausted retries")

    def leader_snapshot(self) -> dict[str, Any]:
        for _ in range(self._MAX_CAS_ATTEMPTS):
            entry, state, compares, cleanup, expired, now = self._load()
            leader = state["coordinator"]["leader"]
            key, _ = self.store.linearizable_get(self._LEADER_KEY)
            active = (
                self._valid_leader_record(leader)
                and key is not None
                and key.value == self.scheduler._encode(leader)
                and float(leader["expires_at"]) > now
            )
            result = self._commit_read(entry, state, compares, cleanup, expired, ())
            if result.succeeded:
                return {
                    "leader_id": None if leader is None else leader["leader_id"],
                    "epoch": 0 if leader is None else int(leader["epoch"]),
                    "expires_at": 0.0 if leader is None else float(leader["expires_at"]),
                    "active": bool(active),
                }
        raise CoordinatorAuthorityUnavailableError("Leader snapshot exhausted retries")

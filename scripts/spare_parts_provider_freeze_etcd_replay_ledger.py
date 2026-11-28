#!/usr/bin/env python3
"""Shared etcd CAS/Txn replay ledger for Provider freeze attestations.

All evidence/nonce/freeze-generation uniqueness keys are created in one
transaction with exact Coordinator aggregate and native Leader-key revision
guards. The included InMemoryEtcdV3Client tests are contract tests only; they
are not evidence of a real etcd cluster or Provider freeze enforcement.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.spare_parts_migration_namespace import (
    MigrationNamespaceError,
    validate_isolated_namespace,
)
from scripts.spare_parts_provider_authority_store import (
    AuthorityStoreCompare,
    AuthorityStoreOutcomeUnknownError,
    AuthorityStorePut,
)
from scripts.spare_parts_sqlite_provider_fencing_reconciliation import (
    ProviderFencingReconciliationError,
    _canonical,
)
from scripts.spare_parts_sqlite_provider_freeze_attestation import (
    COORDINATOR_SNAPSHOT_FORMAT,
    ProviderFreezeReplayError,
    ProviderFreezeReplayLedgerError,
)


class ProviderFreezeAuthorityChangedError(ProviderFencingReconciliationError):
    """Raised when Coordinator authority changes before replay consumption."""


class ProviderFreezeReplayOutcomeUnknownError(ProviderFreezeReplayLedgerError):
    """Raised when an etcd write outcome cannot be proven by read-back."""


class EtcdProviderFreezeEvidenceReplayLedger:
    """Consume replay identifiers with one shared, linearizable etcd Txn.

    The ledger writes four permanent keys (evidence ID, challenge nonce,
    freeze generation and freeze ID) atomically. The same Txn compares the
    exact Scheduler aggregate and Coordinator native Leader TTL key revisions
    observed immediately before submission. The namespace must be an isolated
    migration namespace, never the production Unified prefix.
    """

    FORMAT = "ch17-provider-freeze-etcd-replay-ledger-v1"

    def __init__(self, store: Any, *, namespace_prefix: bytes) -> None:
        validate_isolated_namespace(namespace_prefix)
        required = ("linearizable_get", "transact")
        if any(not callable(getattr(store, name, None)) for name in required):
            raise ProviderFreezeReplayLedgerError(
                "replay ledger requires a CoordinatorAuthorityStore Get/Txn port"
            )
        self.store = store
        self.namespace_prefix = namespace_prefix
        self.state_key = namespace_prefix + b"scheduler/state"
        self.leader_key = namespace_prefix + b"coordinator/leader"
        self.root = namespace_prefix + b"provider-freeze-replay/v1/"

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _keys(self, record: dict[str, Any]) -> tuple[bytes, ...]:
        provider = self._digest(record["provider_id"])
        evidence = self._digest(record["evidence_id"])
        nonce = record["challenge_nonce_sha256"]
        freeze = self._digest(record["freeze_id"])
        generation = record["freeze_generation"]
        return (
            self.root + b"providers/" + provider.encode("ascii") + b"/evidence/" + evidence.encode("ascii"),
            self.root + b"providers/" + provider.encode("ascii") + b"/nonces/" + nonce.encode("ascii"),
            self.root + b"providers/" + provider.encode("ascii") + b"/freeze-generations/" + f"{generation:020d}".encode("ascii"),
            self.root + b"providers/" + provider.encode("ascii") + b"/freeze-ids/" + freeze.encode("ascii"),
        )

    @staticmethod
    def _validate_record(record: dict[str, Any]) -> None:
        required = {
            "provider_id", "evidence_id", "challenge_nonce_sha256",
            "claim_sha256", "freeze_id", "freeze_generation", "leader_id",
            "leader_epoch", "lease_id", "consumed_at_unix",
        }
        if not isinstance(record, dict) or set(record) != required:
            raise ProviderFreezeReplayLedgerError("replay ledger record schema mismatch")
        for field in ("provider_id", "evidence_id", "claim_sha256", "freeze_id", "leader_id"):
            if not isinstance(record[field], str) or not record[field].strip():
                raise ProviderFreezeReplayLedgerError(f"{field} must be non-empty")
        for field in ("freeze_generation", "leader_epoch", "lease_id"):
            if not isinstance(record[field], int) or isinstance(record[field], bool) or record[field] <= 0:
                raise ProviderFreezeReplayLedgerError(f"{field} must be a positive integer")
        digest = record["challenge_nonce_sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ProviderFreezeReplayLedgerError("challenge nonce digest is invalid")
        if (
            not isinstance(record["consumed_at_unix"], (int, float))
            or isinstance(record["consumed_at_unix"], bool)
        ):
            raise ProviderFreezeReplayLedgerError("consumed_at_unix is invalid")

    def _read_authority(self, record: dict[str, Any], authority_snapshot: dict[str, Any]):
        if not isinstance(authority_snapshot, dict) or set(authority_snapshot) != {
            "format", "observed_at_unix", "leader_id", "leader_epoch",
            "lease_id", "lease_expires_at_unix", "scopes",
        } or authority_snapshot.get("format") != COORDINATOR_SNAPSHOT_FORMAT:
            raise ProviderFreezeAuthorityChangedError("Coordinator snapshot schema mismatch")
        if (
            authority_snapshot.get("leader_id") != record["leader_id"]
            or authority_snapshot.get("leader_epoch") != record["leader_epoch"]
            or authority_snapshot.get("lease_id") != record["lease_id"]
        ):
            raise ProviderFreezeAuthorityChangedError(
                "Coordinator snapshot identity does not match replay record"
            )
        try:
            state_entry, _ = self.store.linearizable_get(self.state_key)
            leader_entry, _ = self.store.linearizable_get(self.leader_key)
        except Exception as exc:
            raise ProviderFreezeReplayLedgerError(
                "linearizable Coordinator authority read failed closed"
            ) from exc
        if state_entry is None or leader_entry is None:
            raise ProviderFreezeAuthorityChangedError(
                "Coordinator aggregate or native Leader TTL key is absent"
            )
        if leader_entry.lease_id != record["lease_id"]:
            raise ProviderFreezeAuthorityChangedError(
                "Coordinator native Leader key is attached to another Lease"
            )
        try:
            state = json.loads(state_entry.value.decode("utf-8"))
            leader_value = json.loads(leader_entry.value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderFreezeReplayLedgerError(
                "Coordinator authority state is malformed"
            ) from exc
        coordinator = state.get("coordinator") if isinstance(state, dict) else None
        if not isinstance(coordinator, dict):
            raise ProviderFreezeReplayLedgerError("Coordinator aggregate section is missing")
        current_leader = coordinator.get("leader")
        scopes = coordinator.get("scopes")
        if not isinstance(current_leader, dict) or not isinstance(scopes, dict):
            raise ProviderFreezeAuthorityChangedError("Coordinator Leader or scope state is absent")
        if (
            leader_value != current_leader
            or current_leader.get("leader_id") != record["leader_id"]
            or current_leader.get("epoch") != record["leader_epoch"]
            or current_leader.get("backend_lease_id") != record["lease_id"]
            or current_leader.get("expires_at") != authority_snapshot.get("lease_expires_at_unix")
            or float(current_leader.get("expires_at", 0)) <= float(record["consumed_at_unix"])
        ):
            raise ProviderFreezeAuthorityChangedError(
                "Coordinator native Leader and aggregate do not match signed freeze binding"
            )
        if scopes != authority_snapshot.get("scopes"):
            raise ProviderFreezeAuthorityChangedError(
                "Coordinator scope floors changed after the signed freeze snapshot"
            )
        compares = (
            AuthorityStoreCompare(self.state_key, "MOD", "EQUAL", state_entry.mod_revision),
            AuthorityStoreCompare(self.state_key, "VALUE", "EQUAL", state_entry.value),
            AuthorityStoreCompare(self.leader_key, "MOD", "EQUAL", leader_entry.mod_revision),
            AuthorityStoreCompare(self.leader_key, "VALUE", "EQUAL", leader_entry.value),
        )
        return compares, state_entry, leader_entry

    def _classify_keys(self, keys: tuple[bytes, ...], payload: bytes) -> str:
        try:
            entries = [self.store.linearizable_get(key)[0] for key in keys]
        except Exception as exc:
            raise ProviderFreezeReplayOutcomeUnknownError(
                "replay-key read-back failed; consume outcome remains unknown"
            ) from exc
        if all(entry is None for entry in entries):
            return "ABSENT"
        if all(
            entry is not None and entry.value == payload and entry.lease_id == 0
            for entry in entries
        ):
            return "MATCH"
        raise ProviderFreezeReplayLedgerError(
            "replay ledger contains a partial or conflicting record; quarantine required"
        )

    def _submit(
        self,
        keys: tuple[bytes, ...],
        payload: bytes,
        authority_compares: tuple[AuthorityStoreCompare, ...],
    ):
        compares = tuple(
            AuthorityStoreCompare(key, "VERSION", "EQUAL", 0) for key in keys
        ) + authority_compares
        puts = tuple(AuthorityStorePut(key, payload) for key in keys)
        return self.store.transact(compares, puts, ())

    def consume_once(
        self,
        record: dict[str, Any],
        *,
        authority_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_record(record)
        payload_record = {
            "format": self.FORMAT,
            "record": record,
            "authority_snapshot_sha256": hashlib.sha256(
                _canonical(authority_snapshot)
            ).hexdigest(),
        }
        payload = _canonical(payload_record)
        keys = self._keys(record)

        # A known pre-existing record is a replay. Partial state is corruption,
        # not an opportunity to repair the ledger silently.
        state = self._classify_keys(keys, payload)
        if state != "ABSENT":
            raise ProviderFreezeReplayError("Provider freeze evidence was already consumed")

        authority_compares, _, _ = self._read_authority(record, authority_snapshot)
        try:
            result = self._submit(keys, payload, authority_compares)
            if result.succeeded:
                return {"status": "CONSUMED", "revision": result.revision}
            observed = self._classify_keys(keys, payload)
            if observed == "MATCH":
                raise ProviderFreezeReplayError(
                    "Provider freeze evidence was consumed by another caller"
                )
            raise ProviderFreezeAuthorityChangedError(
                "Coordinator authority changed before replay consumption Txn"
            )
        except AuthorityStoreOutcomeUnknownError:
            observed = self._classify_keys(keys, payload)
            if observed == "MATCH":
                return {"status": "CONFIRMED_AFTER_UNKNOWN", "revision": None}
            # All keys are absent at a linearizable read point. Rebuild the
            # authority compares, then retry exactly the same idempotent Txn.
            retry_authority, _, _ = self._read_authority(record, authority_snapshot)
            try:
                retry = self._submit(keys, payload, retry_authority)
                if retry.succeeded:
                    return {"status": "RETRIED_AFTER_NOT_COMMITTED", "revision": retry.revision}
                observed = self._classify_keys(keys, payload)
                if observed == "MATCH":
                    raise ProviderFreezeReplayError(
                        "Provider freeze evidence was consumed by another caller"
                    )
                raise ProviderFreezeAuthorityChangedError(
                    "Coordinator authority changed before the exact retry"
                )
            except AuthorityStoreOutcomeUnknownError as retry_exc:
                observed = self._classify_keys(keys, payload)
                if observed == "MATCH":
                    return {"status": "CONFIRMED_AFTER_RETRY_UNKNOWN", "revision": None}
                raise ProviderFreezeReplayOutcomeUnknownError(
                    "exact replay-consumption retry remains unknown; do not activate"
                ) from retry_exc

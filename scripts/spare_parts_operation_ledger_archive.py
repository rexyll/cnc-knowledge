#!/usr/bin/env python3
"""Pure in-memory reference model for safe Coordinator operation-ledger archival.

This module is deliberately not wired into StoreBackedCoordinatorAuthority.
It models the archive protocol and its failure boundaries using synthetic
records and an immutable in-memory archive object store only.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Callable


PENDING_STATES = {
    "PENDING_ACTIVATION",
    "REVOKING",
    "PENDING_PUBLISH",
    "RECOVERY_REVIEW",
}
TERMINAL_STATES = {"REVOKED", "COMMITTED"}
INACTIVE_SCOPE_STATES = {
    "IDLE",
    "REVOKED",
    "FENCED",
    "RECOVERY_REQUIRED",
}


class OperationArchiveError(RuntimeError):
    """Base exception for the archive reference model."""


class OperationArchiveUnavailableError(OperationArchiveError):
    """Archive storage or authoritative metadata cannot be read."""


class OperationArchiveIntegrityError(OperationArchiveError):
    """An archive object or manifest chain is missing or corrupt."""


class OperationArchiveConflictError(OperationArchiveError):
    """An idempotency key or immutable object conflicts with prior data."""


class OperationArchiveOutcomeUnknownError(OperationArchiveUnavailableError):
    """A write may have committed, but authoritative read-back was unavailable."""


class OperationArchiveCasConflictError(OperationArchiveConflictError):
    """The scope revision changed while an archive object was being prepared."""


class OperationArchivePolicyError(OperationArchiveError):
    """A caller supplied an invalid or insufficiently large archive policy."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise OperationArchiveIntegrityError(
            "archive data is not canonical JSON"
        ) from exc


def operation_index_key(scope: str, idempotency_key: str) -> str:
    raw = (scope + "\x00" + idempotency_key).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def make_operation(
    *,
    scope: str,
    kind: str,
    idempotency_key: str,
    request_sha256: str,
    state: str,
    fencing_token: int = 1,
    operation_sequence: int | None = None,
    lease_id: str = "lease-1",
    owner_id: str = "owner-1",
    tenant_id: str = "tenant-1",
    domain: str = "write",
    lease_expires_at: float = 2_000_000_000.0,
    provider_generation: str | None = None,
    manifest_key: str | None = None,
    manifest_sha256: str | None = None,
    created_at: float = 1_800_000_000.0,
    updated_at: float = 1_800_000_000.0,
) -> dict[str, Any]:
    if len(request_sha256) != 64:
        raise ValueError("request_sha256 must be a 64-character hex digest")
    return {
        "scope": scope,
        "kind": kind,
        "idempotency_key": idempotency_key,
        "request_sha256": request_sha256,
        "fencing_token": fencing_token,
        "operation_sequence": operation_sequence,
        "lease_id": lease_id,
        "owner_id": owner_id,
        "tenant_id": tenant_id,
        "domain": domain,
        "lease_expires_at": lease_expires_at,
        "state": state,
        "provider_generation": provider_generation,
        "manifest_key": manifest_key,
        "manifest_sha256": manifest_sha256,
        "created_at": created_at,
        "updated_at": updated_at,
    }


class InMemoryImmutableOperationArchiveStore:
    """Content-addressed immutable object store test double.

    Objects are keyed by SHA-256. There is intentionally no delete method:
    orphan reclamation is outside this reference protocol and requires a
    separately approved inventory/retention process.
    """

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self.fail_next_put = False
        self.fail_next_read = False
        self.lose_next_put_response = False

    def put_immutable(self, payload: bytes) -> str:
        if not isinstance(payload, bytes) or not payload:
            raise OperationArchivePolicyError("archive payload must be non-empty bytes")
        digest = hashlib.sha256(payload).hexdigest()
        if self.fail_next_put:
            self.fail_next_put = False
            raise OperationArchiveUnavailableError("archive object write unavailable")
        existing = self._objects.get(digest)
        if existing is not None and existing != payload:
            raise OperationArchiveIntegrityError(
                "content-address collision returned different bytes"
            )
        self._objects.setdefault(digest, payload)
        if self.lose_next_put_response:
            self.lose_next_put_response = False
            raise OperationArchiveOutcomeUnknownError(
                "immutable archive write response was lost"
            )
        return digest

    def read(self, digest: str) -> bytes:
        if self.fail_next_read:
            self.fail_next_read = False
            raise OperationArchiveUnavailableError("archive object read unavailable")
        value = self._objects.get(digest)
        if value is None:
            raise OperationArchiveIntegrityError(
                "authoritative archive pointer references a missing object"
            )
        return value

    def corrupt_for_test(self, digest: str, payload: bytes) -> None:
        """Test-only fault injection; never used by normal archive operations."""
        if digest not in self._objects:
            raise KeyError(digest)
        self._objects[digest] = payload

    @property
    def object_count(self) -> int:
        return len(self._objects)


class OperationLedgerArchiveModel:
    """In-memory scope authority plus immutable archive protocol model.

    Active/pending operations stay hot. Eligible terminal operation records are
    written and read back from immutable storage before the hot index is
    modified. A per-scope manifest head is then switched using an in-memory
    revision compare, modelling the authoritative Coordinator CAS.
    """

    _MANIFEST_FIELDS = {
        "schema_version",
        "scope",
        "generation",
        "previous_batch_sha256",
        "records",
    }
    _INDEX_ROW_FIELDS = {"operation_key", "record"}
    _RECORD_FIELDS = {
        "scope",
        "kind",
        "idempotency_key",
        "request_sha256",
        "fencing_token",
        "operation_sequence",
        "lease_id",
        "owner_id",
        "tenant_id",
        "domain",
        "lease_expires_at",
        "state",
        "provider_generation",
        "manifest_key",
        "manifest_sha256",
        "created_at",
        "updated_at",
    }

    def __init__(self, archive_store: InMemoryImmutableOperationArchiveStore) -> None:
        self.archive_store = archive_store
        self.scopes: dict[str, dict[str, Any]] = {}
        self.hot_operations: dict[str, dict[str, Any]] = {}
        self._scope_revisions: dict[str, int] = {}
        self.scope_read_available = True
        self.lose_next_commit_response = False

    def create_scope(
        self,
        scope: str,
        *,
        high_water_token: int = 0,
        latest_operation_sequence: int = 0,
        lease_state: str = "IDLE",
        lease_id: str | None = None,
    ) -> None:
        if not isinstance(scope, str) or not scope.startswith("tenants/"):
            raise OperationArchivePolicyError("scope must use the tenants/<id>/ namespace")
        if scope in self.scopes:
            raise OperationArchiveConflictError("scope already exists")
        for value, label in (
            (high_water_token, "high-water token"),
            (latest_operation_sequence, "operation sequence"),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise OperationArchivePolicyError(f"{label} must be a non-negative integer")
        self.scopes[scope] = {
            "scope": scope,
            "high_water_token": high_water_token,
            "latest_operation_sequence": latest_operation_sequence,
            "lease_state": lease_state,
            "lease_id": lease_id,
            "archive_generation": 0,
            "archive_head_sha256": None,
            "archived_operation_count": 0,
        }
        self._scope_revisions[scope] = 1

    def _validate_operation(self, record: dict[str, Any]) -> None:
        if not isinstance(record, dict) or set(record) != self._RECORD_FIELDS:
            raise OperationArchiveIntegrityError("operation record schema mismatch")
        if record.get("scope") not in self.scopes:
            raise OperationArchivePolicyError("operation references an unknown scope")
        if not isinstance(record.get("kind"), str) or not record["kind"]:
            raise OperationArchiveIntegrityError("operation kind is missing")
        if not isinstance(record.get("idempotency_key"), str) or not record["idempotency_key"]:
            raise OperationArchiveIntegrityError("operation idempotency key is missing")
        if (
            not isinstance(record.get("request_sha256"), str)
            or len(record["request_sha256"]) != 64
        ):
            raise OperationArchiveIntegrityError("operation request digest is malformed")
        for key in ("fencing_token",):
            if not isinstance(record.get(key), int) or isinstance(record[key], bool) or record[key] < 1:
                raise OperationArchiveIntegrityError(f"operation {key} is invalid")
        sequence = record.get("operation_sequence")
        if sequence is not None and (
            not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1
        ):
            raise OperationArchiveIntegrityError("operation sequence is invalid")
        for key in ("created_at", "updated_at", "lease_expires_at"):
            value = record.get(key)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
            ):
                raise OperationArchiveIntegrityError(f"operation {key} is invalid")
        if record.get("state") not in (
            PENDING_STATES | TERMINAL_STATES | {"ACTIVE"}
        ):
            raise OperationArchiveIntegrityError("operation state is unknown")

    def insert_or_replay(self, record: dict[str, Any]) -> dict[str, Any]:
        """Model the idempotency check before a new operation is allocated."""
        self._validate_operation(record)
        key = operation_index_key(record["scope"], record["idempotency_key"])
        existing = self._lookup_exact(record["scope"], record["idempotency_key"])
        if existing is not None:
            if (
                existing["kind"] != record["kind"]
                or existing["request_sha256"] != record["request_sha256"]
            ):
                raise OperationArchiveConflictError(
                    "idempotency key was reused for a different operation or payload"
                )
            return dict(existing)
        self.hot_operations[key] = dict(record)
        scope_state = self.scopes[record["scope"]]
        scope_state["high_water_token"] = max(
            int(scope_state["high_water_token"]), int(record["fencing_token"])
        )
        if record["operation_sequence"] is not None:
            scope_state["latest_operation_sequence"] = max(
                int(scope_state["latest_operation_sequence"]),
                int(record["operation_sequence"]),
            )
        self._scope_revisions[record["scope"]] += 1
        return dict(record)

    def _read_manifest(self, digest: str, scope: str, expected_generation: int) -> dict[str, Any]:
        raw = self.archive_store.read(digest)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise OperationArchiveIntegrityError("archive manifest content hash mismatch")
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OperationArchiveIntegrityError("archive manifest is invalid JSON") from exc
        if (
            not isinstance(manifest, dict)
            or set(manifest) != self._MANIFEST_FIELDS
            or manifest.get("schema_version") != 1
            or manifest.get("scope") != scope
            or manifest.get("generation") != expected_generation
            or not isinstance(manifest.get("records"), list)
        ):
            raise OperationArchiveIntegrityError("archive manifest identity/schema mismatch")
        for row in manifest["records"]:
            if not isinstance(row, dict) or set(row) != self._INDEX_ROW_FIELDS:
                raise OperationArchiveIntegrityError("archive index row schema mismatch")
            self._validate_operation(row["record"])
            if row["record"]["scope"] != scope:
                raise OperationArchiveIntegrityError("archive row crosses scope boundary")
            expected_key = operation_index_key(
                scope, row["record"]["idempotency_key"]
            )
            if row["operation_key"] != expected_key:
                raise OperationArchiveIntegrityError("archive operation key does not match record")
        previous = manifest["previous_batch_sha256"]
        if previous is not None and (
            not isinstance(previous, str) or len(previous) != 64
        ):
            raise OperationArchiveIntegrityError("archive previous pointer is malformed")
        return manifest

    def verify_scope_archive(self, scope: str) -> dict[str, Any]:
        state = self._scope(scope)
        digest = state["archive_head_sha256"]
        generation = int(state["archive_generation"])
        if digest is None:
            if generation != 0 or int(state["archived_operation_count"]) != 0:
                raise OperationArchiveIntegrityError("empty archive head has non-empty counters")
            return {"batch_count": 0, "operation_count": 0, "head_sha256": None}
        if generation < 1:
            raise OperationArchiveIntegrityError("archive generation must be positive")
        expected_generation = generation
        seen: set[str] = set()
        total = 0
        batch_count = 0
        while digest is not None:
            manifest = self._read_manifest(digest, scope, expected_generation)
            for row in manifest["records"]:
                key = row["operation_key"]
                if key in seen:
                    raise OperationArchiveIntegrityError("duplicate operation appears in archive chain")
                seen.add(key)
                total += 1
            digest = manifest["previous_batch_sha256"]
            expected_generation -= 1
            batch_count += 1
        if expected_generation != 0:
            raise OperationArchiveIntegrityError("archive generation chain has a gap")
        if total != int(state["archived_operation_count"]):
            raise OperationArchiveIntegrityError("archive operation count does not match scope head")
        return {
            "batch_count": batch_count,
            "operation_count": total,
            "head_sha256": state["archive_head_sha256"],
        }

    def _lookup_exact(self, scope: str, idempotency_key: str) -> dict[str, Any] | None:
        key = operation_index_key(scope, idempotency_key)
        hot = self.hot_operations.get(key)
        if hot is not None:
            return dict(hot)
        state = self._scope(scope)
        digest = state["archive_head_sha256"]
        if digest is None:
            return None
        generation = int(state["archive_generation"])
        seen: set[str] = set()
        total = 0
        batch_count = 0
        while digest is not None:
            manifest = self._read_manifest(digest, scope, generation)
            for row in manifest["records"]:
                op_key = row["operation_key"]
                if op_key in seen:
                    raise OperationArchiveIntegrityError("duplicate operation appears in archive chain")
                seen.add(op_key)
                total += 1
                if op_key == key:
                    return dict(row["record"])
            digest = manifest["previous_batch_sha256"]
            generation -= 1
            batch_count += 1
        if generation != 0 or total > int(state["archived_operation_count"]):
            raise OperationArchiveIntegrityError("archive chain is incomplete or inconsistent")
        if total != int(state["archived_operation_count"]):
            raise OperationArchiveIntegrityError("archive operation count does not match scope head")
        return None

    def lookup(self, scope: str, idempotency_key: str) -> dict[str, Any] | None:
        return self._lookup_exact(scope, idempotency_key)

    def _scope(self, scope: str) -> dict[str, Any]:
        if not self.scope_read_available:
            raise OperationArchiveUnavailableError(
                "authoritative Coordinator scope state cannot be read"
            )
        try:
            return self.scopes[scope]
        except KeyError as exc:
            raise OperationArchivePolicyError("unknown Coordinator scope") from exc

    def _eligible(
        self,
        record: dict[str, Any],
        scope_state: dict[str, Any],
        *,
        now: float,
        minimum_age_seconds: float,
    ) -> bool:
        if now - float(record["updated_at"]) < minimum_age_seconds:
            return False
        if record["state"] in TERMINAL_STATES:
            return True
        if record["state"] != "ACTIVE" or record["kind"] != "ACTIVATE":
            return False
        is_current_active_lease = (
            scope_state["lease_state"] == "ACTIVE"
            and scope_state["lease_id"] == record["lease_id"]
            and int(scope_state["high_water_token"]) == int(record["fencing_token"])
        )
        return not is_current_active_lease

    def archive_scope(
        self,
        scope: str,
        *,
        now: float,
        minimum_age_seconds: float,
        max_records: int,
        max_batch_bytes: int,
        before_commit: Callable[["OperationLedgerArchiveModel"], None] | None = None,
    ) -> dict[str, Any]:
        """Archive one bounded batch, then CAS-switch the per-scope manifest head.

        If object creation succeeds but the Coordinator compare fails, the
        object is an orphan; hot operations remain authoritative. Orphans are
        never deleted by this model.
        """
        state = self._scope(scope)
        if (
            not isinstance(now, (int, float))
            or isinstance(now, bool)
            or not math.isfinite(float(now))
        ):
            raise OperationArchivePolicyError("archive time must be finite")
        if (
            not isinstance(minimum_age_seconds, (int, float))
            or isinstance(minimum_age_seconds, bool)
            or not math.isfinite(float(minimum_age_seconds))
            or minimum_age_seconds < 0
        ):
            raise OperationArchivePolicyError("minimum age must be finite and non-negative")
        if not isinstance(max_records, int) or isinstance(max_records, bool) or max_records < 1:
            raise OperationArchivePolicyError("max_records must be a positive integer")
        if (
            not isinstance(max_batch_bytes, int)
            or isinstance(max_batch_bytes, bool)
            or max_batch_bytes < 1
        ):
            raise OperationArchivePolicyError("max_batch_bytes must be a positive integer")

        pending = [
            record for record in self.hot_operations.values()
            if record["scope"] == scope and record["state"] in PENDING_STATES
        ]
        if pending:
            return {
                "archived": 0,
                "blocked": True,
                "reason": "scope_contains_unresolved_operations",
                "manifest_sha256": None,
            }

        if state["archive_head_sha256"] is not None:
            self.verify_scope_archive(scope)

        current_revision = self._scope_revisions[scope]
        previous = state["archive_head_sha256"]
        generation = int(state["archive_generation"]) + 1
        eligible = [
            record for record in self.hot_operations.values()
            if record["scope"] == scope
            and self._eligible(
                record,
                state,
                now=float(now),
                minimum_age_seconds=float(minimum_age_seconds),
            )
        ]
        eligible.sort(
            key=lambda record: (
                float(record["updated_at"]),
                record["kind"],
                record["idempotency_key"],
            )
        )
        if not eligible:
            return {
                "archived": 0,
                "blocked": False,
                "reason": "no_eligible_operations",
                "manifest_sha256": None,
            }

        selected: list[dict[str, Any]] = []
        encoded = b""
        for record in eligible:
            candidate = selected + [record]
            manifest = {
                "schema_version": 1,
                "scope": scope,
                "generation": generation,
                "previous_batch_sha256": previous,
                "records": [
                    {
                        "operation_key": operation_index_key(
                            scope, item["idempotency_key"]
                        ),
                        "record": item,
                    }
                    for item in candidate
                ],
            }
            candidate_bytes = canonical_json_bytes(manifest)
            if len(candidate_bytes) > max_batch_bytes:
                if not selected:
                    raise OperationArchivePolicyError(
                        "max_batch_bytes is too small for the next eligible operation"
                    )
                break
            selected = candidate
            encoded = candidate_bytes
            if len(selected) >= max_records:
                break
        if not selected:
            return {
                "archived": 0,
                "blocked": False,
                "reason": "no_batch_selected",
                "manifest_sha256": None,
            }

        expected_digest = hashlib.sha256(encoded).hexdigest()
        try:
            actual_digest = self.archive_store.put_immutable(encoded)
        except OperationArchiveOutcomeUnknownError:
            # An immutable put with a lost response is recoverable by address.
            readback = self.archive_store.read(expected_digest)
            if readback != encoded or hashlib.sha256(readback).hexdigest() != expected_digest:
                raise OperationArchiveOutcomeUnknownError(
                    "archive object put outcome could not be verified"
                )
            actual_digest = expected_digest
        if actual_digest != expected_digest:
            raise OperationArchiveIntegrityError("archive store returned an unexpected digest")
        readback = self.archive_store.read(actual_digest)
        if readback != encoded or hashlib.sha256(readback).hexdigest() != actual_digest:
            raise OperationArchiveIntegrityError("archive object read-back mismatch")

        if before_commit is not None:
            before_commit(self)
        if self._scope_revisions[scope] != current_revision:
            raise OperationArchiveCasConflictError(
                "scope changed while archive batch was prepared; hot ledger is unchanged"
            )
        state = self._scope(scope)
        if state["archive_head_sha256"] != previous:
            raise OperationArchiveCasConflictError(
                "archive head changed while archive batch was prepared"
            )

        state["archive_generation"] = generation
        state["archive_head_sha256"] = actual_digest
        state["archived_operation_count"] = int(state["archived_operation_count"]) + len(selected)
        for record in selected:
            key = operation_index_key(scope, record["idempotency_key"])
            current_record = self.hot_operations.get(key)
            if current_record != record:
                raise OperationArchiveCasConflictError(
                    "hot operation changed before archival compare"
                )
        for record in selected:
            key = operation_index_key(scope, record["idempotency_key"])
            del self.hot_operations[key]
        self._scope_revisions[scope] += 1

        reconciled = False
        if self.lose_next_commit_response:
            self.lose_next_commit_response = False
            if not self.scope_read_available:
                raise OperationArchiveOutcomeUnknownError(
                    "Coordinator archive-head commit may have succeeded; read-back unavailable"
                )
            observed = self.scopes[scope]
            if (
                observed["archive_head_sha256"] != actual_digest
                or int(observed["archive_generation"]) != generation
            ):
                raise OperationArchiveOutcomeUnknownError(
                    "Coordinator archive-head commit outcome is not confirmed"
                )
            reconciled = True

        return {
            "archived": len(selected),
            "blocked": False,
            "reason": "archived",
            "manifest_sha256": actual_digest,
            "archive_generation": generation,
            "archive_operation_count": int(self.scopes[scope]["archived_operation_count"]),
            "archive_object_bytes": len(encoded),
            "outcome_reconciled": reconciled,
        }

    def snapshot(self, scope: str) -> dict[str, Any]:
        state = self._scope(scope)
        return dict(state)

    def hot_operation_count(self, scope: str | None = None) -> int:
        if scope is None:
            return len(self.hot_operations)
        return sum(1 for row in self.hot_operations.values() if row["scope"] == scope)

    def physical_delete_archive_object(self, digest: str) -> None:
        raise OperationArchivePolicyError(
            "archive object deletion is not implemented; orphan/retention GC requires a separately approved protocol"
        )

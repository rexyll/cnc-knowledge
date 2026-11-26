#!/usr/bin/env python3
"""Reference state machine for safe Unified Coordinator schema-v2 -> v3 cutover.

The model is synthetic and in-memory only. It specifies a write-frozen,
single-authority migration protocol; it is not connected to etcd or the
production StoreBackedCoordinatorAuthority implementation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any


class CoordinatorSchemaMigrationError(RuntimeError):
    """Base migration state-machine error."""


class CoordinatorSchemaMigrationConflict(CoordinatorSchemaMigrationError):
    """A source revision, leader epoch or control pointer changed."""


class CoordinatorSchemaMigrationIntegrityError(CoordinatorSchemaMigrationError):
    """The candidate snapshot does not exactly represent the v2 source."""


class CoordinatorSchemaMigrationPolicyError(CoordinatorSchemaMigrationError):
    """Migration or rollback policy is invalid or insufficient."""


def canonical_state_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CoordinatorSchemaMigrationIntegrityError(
            "migration state is not canonical JSON"
        ) from exc


def state_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_state_bytes(value)).hexdigest()


def _positive_or_zero_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CoordinatorSchemaMigrationIntegrityError(
            f"{label} must be a non-negative integer"
        )
    return value


class CoordinatorSchemaMigrationModel:
    """Write-frozen migration controller and schema-v3 logical object model.

    V3 separates scheduler core/leases/waiters, Leader, scope rows and hot
    operation rows into independently addressed objects. Archive index
    pointers remain per-scope metadata. The reference model stores those
    objects in memory and uses one control pointer to model atomic cutover.
    """

    def __init__(
        self,
        v2_state: dict[str, Any],
        *,
        source_revision: int = 1,
        leader_epoch: int = 1,
    ) -> None:
        self._validate_v2(v2_state)
        if source_revision < 1 or leader_epoch < 1:
            raise CoordinatorSchemaMigrationPolicyError(
                "source revision and leader epoch must be positive"
            )
        self.v2_state = copy.deepcopy(v2_state)
        self.v2_revision = source_revision
        self.leader_epoch = leader_epoch
        self.control_epoch = 1
        self.active_schema = 2
        self.migration_epoch = 0
        self.migration_status = "IDLE"
        self.writes_frozen = False
        self.v3_writes_started = False
        self.source_snapshot: dict[str, Any] | None = None
        self.source_revision: int | None = None
        self.source_sha256: str | None = None
        self.candidate_root: dict[str, Any] | None = None
        self.candidate_sha256: str | None = None
        self.v3_objects: dict[str, bytes] = {}
        self.v3_scopes: dict[str, dict[str, Any]] = {}
        self.v3_hot_operations: dict[str, dict[str, Any]] = {}
        self.archive_index_pointers: dict[str, dict[str, Any]] = {}
        self.known_operation_keys: set[str] = set()

    @staticmethod
    def _validate_v2(state: dict[str, Any]) -> None:
        if not isinstance(state, dict) or state.get("schema_version") != 2:
            raise CoordinatorSchemaMigrationIntegrityError(
                "migration source must be a schema-v2 aggregate"
            )
        required = {
            "schema_version",
            "policy_hash",
            "global_limits",
            "tenant_limits",
            "max_waiters",
            "aging_interval_seconds",
            "next_fencing_token",
            "next_waiter_sequence",
            "active",
            "waiters",
            "coordinator",
            "counters",
        }
        if set(state) != required:
            raise CoordinatorSchemaMigrationIntegrityError(
                "schema-v2 aggregate top-level fields mismatch"
            )
        coordinator = state["coordinator"]
        if (
            not isinstance(coordinator, dict)
            or set(coordinator) != {"leader", "scopes", "operations"}
            or not isinstance(coordinator["scopes"], dict)
            or not isinstance(coordinator["operations"], dict)
        ):
            raise CoordinatorSchemaMigrationIntegrityError(
                "schema-v2 Coordinator structure is malformed"
            )
        if not isinstance(state["active"], dict) or not isinstance(state["waiters"], list):
            raise CoordinatorSchemaMigrationIntegrityError(
                "schema-v2 Admission state is malformed"
            )
        if not isinstance(state["counters"], dict):
            raise CoordinatorSchemaMigrationIntegrityError(
                "schema-v2 counters are malformed"
            )
        _positive_or_zero_int(state["next_fencing_token"], "next_fencing_token")
        _positive_or_zero_int(state["next_waiter_sequence"], "next_waiter_sequence")
        for scope, row in coordinator["scopes"].items():
            if not isinstance(scope, str) or not isinstance(row, dict):
                raise CoordinatorSchemaMigrationIntegrityError(
                    "schema-v2 scope record is malformed"
                )
            _positive_or_zero_int(row.get("high_water_token"), "scope high_water_token")
            _positive_or_zero_int(
                row.get("latest_operation_sequence"),
                "scope latest_operation_sequence",
            )
        for key, record in coordinator["operations"].items():
            if not isinstance(key, str) or not isinstance(record, dict):
                raise CoordinatorSchemaMigrationIntegrityError(
                    "schema-v2 operation record is malformed"
                )
            if record.get("scope") not in coordinator["scopes"]:
                raise CoordinatorSchemaMigrationIntegrityError(
                    "operation refers to a missing scope"
                )
            _positive_or_zero_int(record.get("fencing_token"), "operation fencing_token")
            sequence = record.get("operation_sequence")
            if sequence is not None:
                _positive_or_zero_int(sequence, "operation operation_sequence")

    def _scope_floors(self, state: dict[str, Any]) -> dict[str, dict[str, int]]:
        result = {}
        for scope, row in state["coordinator"]["scopes"].items():
            result[scope] = {
                "high_water_token": int(row["high_water_token"]),
                "latest_operation_sequence": int(row["latest_operation_sequence"]),
            }
        return result

    def _operations_by_scope(self, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        output: dict[str, dict[str, Any]] = {
            scope: {} for scope in state["coordinator"]["scopes"]
        }
        for key, row in state["coordinator"]["operations"].items():
            output[row["scope"]][key] = copy.deepcopy(row)
        return output

    def mutate_v2(self, operation_key: str, record: dict[str, Any]) -> None:
        """Synthetic write path used to prove migration freeze and revision guards."""
        if self.active_schema != 2 or self.writes_frozen:
            raise CoordinatorSchemaMigrationConflict(
                "schema-v2 writes are frozen or v2 is no longer active"
            )
        if not isinstance(operation_key, str) or not operation_key:
            raise CoordinatorSchemaMigrationPolicyError("operation key is required")
        if operation_key in self.v2_state["coordinator"]["operations"]:
            raise CoordinatorSchemaMigrationConflict("operation key already exists")
        self._validate_new_operation(record, self.v2_state)
        self.v2_state["coordinator"]["operations"][operation_key] = copy.deepcopy(record)
        scope = record["scope"]
        scope_row = self.v2_state["coordinator"]["scopes"][scope]
        scope_row["high_water_token"] = max(
            int(scope_row["high_water_token"]), int(record["fencing_token"])
        )
        sequence = record.get("operation_sequence")
        if sequence is not None:
            scope_row["latest_operation_sequence"] = max(
                int(scope_row["latest_operation_sequence"]), int(sequence)
            )
        self.v2_revision += 1

    @staticmethod
    def _validate_new_operation(record: dict[str, Any], state: dict[str, Any]) -> None:
        if not isinstance(record, dict) or record.get("scope") not in state["coordinator"]["scopes"]:
            raise CoordinatorSchemaMigrationPolicyError(
                "new operation must reference an existing scope"
            )
        _positive_or_zero_int(record.get("fencing_token"), "new operation fencing_token")
        seq = record.get("operation_sequence")
        if seq is not None:
            _positive_or_zero_int(seq, "new operation operation_sequence")

    def begin_migration(self, *, expected_leader_epoch: int) -> dict[str, Any]:
        if self.active_schema != 2 or self.migration_status not in {
            "IDLE",
            "ROLLED_BACK_PRE_WRITE",
        }:
            raise CoordinatorSchemaMigrationConflict("schema migration is already active")
        if expected_leader_epoch != self.leader_epoch:
            raise CoordinatorSchemaMigrationConflict(
                "migration caller does not hold the current Leader epoch"
            )
        self.writes_frozen = True
        self.migration_epoch += 1
        self.migration_status = "SOURCE_FROZEN"
        self.source_snapshot = copy.deepcopy(self.v2_state)
        self.source_revision = self.v2_revision
        self.source_sha256 = state_sha256(self.source_snapshot)
        self.candidate_root = None
        self.candidate_sha256 = None
        self.v3_objects = {}
        return {
            "migration_epoch": self.migration_epoch,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
            "leader_epoch": self.leader_epoch,
            "writes_frozen": True,
        }

    def build_v3_candidate(
        self,
        *,
        archive_index_pointers: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if (
            not self.writes_frozen
            or self.migration_status != "SOURCE_FROZEN"
            or self.source_snapshot is None
        ):
            raise CoordinatorSchemaMigrationConflict(
                "candidate build requires a frozen v2 source snapshot"
            )
        source = self.source_snapshot
        scopes = source["coordinator"]["scopes"]
        pointers = copy.deepcopy(archive_index_pointers or {})
        if not isinstance(pointers, dict) or set(pointers) - set(scopes):
            raise CoordinatorSchemaMigrationPolicyError(
                "archive index pointers must be keyed by an existing Coordinator scope"
            )
        for scope, pointer in pointers.items():
            required_pointer = {
                "scope", "index_generation", "index_head_sha256",
                "archive_generation", "archive_head_sha256",
                "operation_count", "bucket_count",
            }
            if (
                not isinstance(pointer, dict)
                or set(pointer) != required_pointer
                or pointer.get("scope") != scope
                or not isinstance(pointer.get("index_generation"), int)
                or isinstance(pointer.get("index_generation"), bool)
                or pointer["index_generation"] < 1
                or pointer.get("index_generation") != pointer.get("archive_generation")
                or pointer.get("bucket_count") not in {16, 256, 4096}
                or not isinstance(pointer.get("index_head_sha256"), str)
                or len(pointer["index_head_sha256"]) != 64
                or any(ch not in "0123456789abcdef" for ch in pointer["index_head_sha256"])
                or not isinstance(pointer.get("archive_head_sha256"), str)
                or len(pointer["archive_head_sha256"]) != 64
                or any(ch not in "0123456789abcdef" for ch in pointer["archive_head_sha256"])
                or not isinstance(pointer.get("operation_count"), int)
                or isinstance(pointer.get("operation_count"), bool)
                or pointer["operation_count"] < 0
            ):
                raise CoordinatorSchemaMigrationPolicyError(
                    "archive index pointer metadata is malformed"
                )
        self.archive_index_pointers = pointers
        operations_by_scope = self._operations_by_scope(source)
        scheduler_core = {
            key: copy.deepcopy(source[key])
            for key in (
                "policy_hash",
                "global_limits",
                "tenant_limits",
                "max_waiters",
                "aging_interval_seconds",
                "next_fencing_token",
                "next_waiter_sequence",
                "counters",
            )
        }
        objects: dict[str, Any] = {
            "scheduler/core": scheduler_core,
            "scheduler/active": copy.deepcopy(source["active"]),
            "scheduler/waiters": copy.deepcopy(source["waiters"]),
            "coordinator/leader": copy.deepcopy(source["coordinator"]["leader"]),
            "coordinator/scopes": copy.deepcopy(scopes),
            "coordinator/hot-operations": operations_by_scope,
            "coordinator/archive-index-pointers": copy.deepcopy(self.archive_index_pointers),
        }
        self.v3_objects = {
            key: canonical_state_bytes(value) for key, value in objects.items()
        }
        object_hashes = {
            key: hashlib.sha256(raw).hexdigest()
            for key, raw in sorted(self.v3_objects.items())
        }
        root = {
            "schema_version": 3,
            "migration_epoch": self.migration_epoch,
            "source_schema_version": 2,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
            "scope_count": len(scopes),
            "operation_count": len(source["coordinator"]["operations"]),
            "object_sha256": object_hashes,
            "scope_floors": self._scope_floors(source),
        }
        self.candidate_root = root
        self.candidate_sha256 = state_sha256(root)
        self.migration_status = "CANDIDATE_BUILT"
        return {
            "schema_version": 3,
            "migration_epoch": self.migration_epoch,
            "candidate_sha256": self.candidate_sha256,
            "scope_count": root["scope_count"],
            "operation_count": root["operation_count"],
            "object_count": len(object_hashes),
        }

    def verify_v3_candidate(self) -> dict[str, Any]:
        if (
            self.migration_status != "CANDIDATE_BUILT"
            or self.source_snapshot is None
            or self.candidate_root is None
        ):
            raise CoordinatorSchemaMigrationConflict("no v3 candidate is ready to verify")
        expected_count = len(self.source_snapshot["coordinator"]["operations"])
        if self.candidate_root["operation_count"] != expected_count:
            raise CoordinatorSchemaMigrationIntegrityError(
                "candidate operation count differs from v2 source"
            )
        for key, digest in self.candidate_root["object_sha256"].items():
            raw = self.v3_objects.get(key)
            if raw is None or hashlib.sha256(raw).hexdigest() != digest:
                raise CoordinatorSchemaMigrationIntegrityError(
                    f"candidate object digest mismatch: {key}"
                )
        expected = self._expected_object_bytes(self.source_snapshot)
        if expected != self.v3_objects:
            raise CoordinatorSchemaMigrationIntegrityError(
                "schema-v3 objects are not an exact representation of the v2 source"
            )
        if self.candidate_root["scope_floors"] != self._scope_floors(
            self.source_snapshot
        ):
            raise CoordinatorSchemaMigrationIntegrityError(
                "candidate fencing or sequence floors differ from source"
            )
        if state_sha256(self.candidate_root) != self.candidate_sha256:
            raise CoordinatorSchemaMigrationIntegrityError("candidate root digest mismatch")
        self.migration_status = "CANDIDATE_VERIFIED"
        return {
            "verified": True,
            "source_sha256": self.source_sha256,
            "candidate_sha256": self.candidate_sha256,
            "operation_count": expected_count,
            "scope_count": len(self.source_snapshot["coordinator"]["scopes"]),
        }

    def _expected_object_bytes(self, state: dict[str, Any]) -> dict[str, bytes]:
        operations_by_scope = self._operations_by_scope(state)
        values = {
            "scheduler/core": {
                key: copy.deepcopy(state[key])
                for key in (
                    "policy_hash",
                    "global_limits",
                    "tenant_limits",
                    "max_waiters",
                    "aging_interval_seconds",
                    "next_fencing_token",
                    "next_waiter_sequence",
                    "counters",
                )
            },
            "scheduler/active": copy.deepcopy(state["active"]),
            "scheduler/waiters": copy.deepcopy(state["waiters"]),
            "coordinator/leader": copy.deepcopy(state["coordinator"]["leader"]),
            "coordinator/scopes": copy.deepcopy(state["coordinator"]["scopes"]),
            "coordinator/hot-operations": operations_by_scope,
            "coordinator/archive-index-pointers": copy.deepcopy(self.archive_index_pointers),
        }
        return {key: canonical_state_bytes(value) for key, value in values.items()}

    def cutover(
        self,
        *,
        expected_source_revision: int,
        expected_leader_epoch: int,
        external_high_water_floors: dict[str, int],
        external_sequence_floors: dict[str, int],
    ) -> dict[str, Any]:
        if (
            not self.writes_frozen
            or self.migration_status != "CANDIDATE_VERIFIED"
            or self.source_snapshot is None
            or self.candidate_root is None
        ):
            raise CoordinatorSchemaMigrationConflict(
                "cutover requires a verified candidate and frozen writers"
            )
        if (
            expected_source_revision != self.source_revision
            or self.v2_revision != self.source_revision
        ):
            raise CoordinatorSchemaMigrationConflict(
                "schema-v2 source revision changed during migration"
            )
        if expected_leader_epoch != self.leader_epoch:
            raise CoordinatorSchemaMigrationConflict(
                "Coordinator Leader epoch changed during migration"
            )
        floors = self.candidate_root["scope_floors"]
        for scope, value in floors.items():
            if external_high_water_floors.get(scope, -1) < value["high_water_token"]:
                raise CoordinatorSchemaMigrationPolicyError(
                    "external fencing high-water floor is below migration source"
                )
            if external_sequence_floors.get(scope, -1) < value["latest_operation_sequence"]:
                raise CoordinatorSchemaMigrationPolicyError(
                    "external operation sequence floor is below migration source"
                )
        self.active_schema = 3
        self.control_epoch += 1
        self.migration_status = "CUTOVER_COMMITTED_FROZEN"
        self.v3_scopes = copy.deepcopy(self.source_snapshot["coordinator"]["scopes"])
        self.v3_hot_operations = copy.deepcopy(
            self.source_snapshot["coordinator"]["operations"]
        )
        self.known_operation_keys = set(self.v3_hot_operations)
        return {
            "active_schema": self.active_schema,
            "control_epoch": self.control_epoch,
            "candidate_sha256": self.candidate_sha256,
            "writes_frozen": True,
            "v3_writes_started": False,
        }

    def resume_v3_writes(self) -> None:
        if (
            self.active_schema != 3
            or self.migration_status != "CUTOVER_COMMITTED_FROZEN"
            or not self.writes_frozen
        ):
            raise CoordinatorSchemaMigrationConflict(
                "v3 writes can resume only after committed frozen cutover"
            )
        self.writes_frozen = False
        self.migration_status = "ACTIVE_V3_NO_WRITES_YET"

    def record_v3_operation(self, operation_key: str, record: dict[str, Any]) -> None:
        if self.active_schema != 3 or self.writes_frozen:
            raise CoordinatorSchemaMigrationConflict(
                "schema-v3 writes are not enabled"
            )
        if not isinstance(operation_key, str) or not operation_key:
            raise CoordinatorSchemaMigrationPolicyError("operation key is required")
        if operation_key in self.v3_hot_operations:
            raise CoordinatorSchemaMigrationConflict("v3 operation key already exists")
        if not isinstance(record, dict) or record.get("scope") not in self.v3_scopes:
            raise CoordinatorSchemaMigrationPolicyError(
                "v3 operation must reference an existing scope"
            )
        token = _positive_or_zero_int(record.get("fencing_token"), "v3 fencing token")
        sequence = record.get("operation_sequence")
        if sequence is not None:
            _positive_or_zero_int(sequence, "v3 operation sequence")
        scope_row = self.v3_scopes[record["scope"]]
        if token < int(scope_row["high_water_token"]):
            raise CoordinatorSchemaMigrationPolicyError(
                "v3 operation attempted to lower the fencing high-water mark"
            )
        if sequence is not None and sequence < int(scope_row["latest_operation_sequence"]):
            raise CoordinatorSchemaMigrationPolicyError(
                "v3 operation attempted to lower the operation sequence floor"
            )
        self.v3_hot_operations[operation_key] = copy.deepcopy(record)
        scope_row["high_water_token"] = max(int(scope_row["high_water_token"]), token)
        if sequence is not None:
            scope_row["latest_operation_sequence"] = max(
                int(scope_row["latest_operation_sequence"]), sequence
            )
        self.known_operation_keys.add(operation_key)
        self.v3_writes_started = True
        self.migration_status = "ACTIVE_V3_WRITES_STARTED"

    def rollback_before_v3_writes(self) -> dict[str, Any]:
        if (
            self.active_schema != 3
            or not self.writes_frozen
            or self.v3_writes_started
            or self.migration_status != "CUTOVER_COMMITTED_FROZEN"
        ):
            raise CoordinatorSchemaMigrationConflict(
                "pointer rollback is allowed only before v3 accepts any mutation"
            )
        if self.source_snapshot is None or state_sha256(self.source_snapshot) != self.source_sha256:
            raise CoordinatorSchemaMigrationIntegrityError(
                "frozen schema-v2 rollback snapshot no longer verifies"
            )
        self.active_schema = 2
        self.control_epoch += 1
        self.migration_status = "ROLLED_BACK_PRE_WRITE"
        self.writes_frozen = False
        return {
            "active_schema": 2,
            "control_epoch": self.control_epoch,
            "rollback": "PRE_WRITE_POINTER_SWITCH",
            "writes_frozen": False,
        }

    def freeze_v3_for_reverse_migration(self) -> None:
        if self.active_schema != 3 or self.migration_status not in {
            "ACTIVE_V3_NO_WRITES_YET",
            "ACTIVE_V3_WRITES_STARTED",
        }:
            raise CoordinatorSchemaMigrationConflict("schema-v3 is not active")
        self.writes_frozen = True
        self.migration_status = "V3_FROZEN_FOR_REVERSE_MIGRATION"

    def reverse_migrate_to_v2(
        self,
        rehydrated_v2_state: dict[str, Any],
        *,
        archive_lookup_complete: bool,
        external_high_water_floors: dict[str, int],
        external_sequence_floors: dict[str, int],
        max_v2_state_bytes: int,
    ) -> dict[str, Any]:
        """Explicit reverse migration after rehydration; never reuse stale v2 snapshot."""
        if (
            self.active_schema != 3
            or not self.writes_frozen
            or self.migration_status != "V3_FROZEN_FOR_REVERSE_MIGRATION"
        ):
            raise CoordinatorSchemaMigrationConflict(
                "reverse migration requires v3 writes to be frozen"
            )
        if archive_lookup_complete is not True:
            raise CoordinatorSchemaMigrationIntegrityError(
                "archive chain and exact index must be fully rehydrated before rollback"
            )
        self._validate_v2(rehydrated_v2_state)
        if (
            not isinstance(max_v2_state_bytes, int)
            or isinstance(max_v2_state_bytes, bool)
            or max_v2_state_bytes < 1
        ):
            raise CoordinatorSchemaMigrationPolicyError("max_v2_state_bytes must be positive")
        size = len(canonical_state_bytes(rehydrated_v2_state))
        if size > max_v2_state_bytes:
            raise CoordinatorSchemaMigrationPolicyError(
                "rehydrated schema-v2 aggregate exceeds the approved size ceiling"
            )

        operations = rehydrated_v2_state["coordinator"]["operations"]
        missing = self.known_operation_keys - set(operations)
        if missing:
            raise CoordinatorSchemaMigrationIntegrityError(
                "reverse migration omitted operations accepted by schema-v3"
            )
        v3_floors = self._v3_floors()
        v2_floors = self._scope_floors(rehydrated_v2_state)
        for scope, floor in v3_floors.items():
            if scope not in v2_floors:
                raise CoordinatorSchemaMigrationIntegrityError(
                    "reverse migration omitted a schema-v3 scope"
                )
            if (
                v2_floors[scope]["high_water_token"] < floor["high_water_token"]
                or v2_floors[scope]["latest_operation_sequence"]
                < floor["latest_operation_sequence"]
            ):
                raise CoordinatorSchemaMigrationIntegrityError(
                    "reverse migration lowered a schema-v3 fencing/sequence floor"
                )
            if external_high_water_floors.get(scope, -1) < floor["high_water_token"]:
                raise CoordinatorSchemaMigrationPolicyError(
                    "external fencing floor is below active schema-v3 floor"
                )
            if external_sequence_floors.get(scope, -1) < floor["latest_operation_sequence"]:
                raise CoordinatorSchemaMigrationPolicyError(
                    "external sequence floor is below active schema-v3 floor"
                )

        self.v2_state = copy.deepcopy(rehydrated_v2_state)
        self.v2_revision += 1
        self.active_schema = 2
        self.control_epoch += 1
        self.migration_status = "REVERSE_MIGRATED_TO_V2"
        self.writes_frozen = False
        return {
            "active_schema": 2,
            "control_epoch": self.control_epoch,
            "rollback": "REBUILT_FROM_V3_AND_ARCHIVE",
            "rehydrated_state_bytes": size,
            "operation_count": len(operations),
            "writes_frozen": False,
        }

    def _v3_floors(self) -> dict[str, dict[str, int]]:
        return {
            scope: {
                "high_water_token": int(row["high_water_token"]),
                "latest_operation_sequence": int(row["latest_operation_sequence"]),
            }
            for scope, row in self.v3_scopes.items()
        }

    def control_pointer(self) -> dict[str, Any]:
        return {
            "active_schema": self.active_schema,
            "control_epoch": self.control_epoch,
            "migration_epoch": self.migration_epoch,
            "migration_status": self.migration_status,
            "writes_frozen": self.writes_frozen,
            "v3_writes_started": self.v3_writes_started,
            "migration_candidate_sha256": self.candidate_sha256,
            "source_v2_sha256": self.source_sha256,
        }

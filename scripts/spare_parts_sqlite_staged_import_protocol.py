#!/usr/bin/env python3
"""Read-only model for checkpointed SQLite-to-Unified schema-v2 import.

This module never connects to etcd. It plans request-index staging transactions,
a small checkpoint CAS chain, and a final scheduler-state publication transaction.
The application namespace must remain inaccessible to application credentials
until the final state transaction is verified and an operator opens the gate.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from scripts.spare_parts_migration_namespace import (
    MigrationNamespaceError,
    validate_isolated_namespace,
)
from scripts.spare_parts_sqlite_candidate_import_plan import (
    _validate_candidate,
)
from scripts.spare_parts_sqlite_migration_inventory import _json_bytes


class StagedImportPlanError(RuntimeError):
    """Raised when a candidate cannot be safely staged or published."""


FORMAT = "ch17-sqlite-staged-import-protocol-v1"
CHECKPOINT_FORMAT = "ch17-sqlite-staged-import-checkpoint-v1"
PRODUCTION_PREFIX = b"/cnc/admission/unified/v2/"
UNKNOWN_COMMITTED = "COMMITTED"
UNKNOWN_RETRY = "NOT_COMMITTED_RETRY_SAME_TXN"
UNKNOWN_QUARANTINE = "INCONSISTENT_QUARANTINE"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StagedImportPlanError("protocol record is not canonical JSON") from exc


def _required_int(value: Any, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise StagedImportPlanError(f"{name} must be an integer >= {minimum}")
    return value


def _wire_request(
    compares: list[dict[str, Any]], puts: list[tuple[bytes, bytes]]
) -> dict[str, Any]:
    return {
        "compare": compares,
        "success": [
            {"request_put": {
                "key": base64.b64encode(key).decode("ascii"),
                "value": base64.b64encode(value).decode("ascii"),
            }}
            for key, value in puts
        ],
        "failure": [],
    }


def _version_zero_compare(key: bytes) -> dict[str, Any]:
    return {
        "key": base64.b64encode(key).decode("ascii"),
        "target": "VERSION",
        "result": "EQUAL",
        "version": "0",
    }


def _value_compare(key: bytes, value: bytes) -> dict[str, Any]:
    return {
        "key": base64.b64encode(key).decode("ascii"),
        "target": "VALUE",
        "result": "EQUAL",
        "value": base64.b64encode(value).decode("ascii"),
    }


def _budget(
    compares: list[dict[str, Any]],
    puts: list[tuple[bytes, bytes]],
    *,
    max_txn_ops: int,
    max_txn_bytes: int,
    margin: int,
) -> dict[str, Any]:
    wire = _canonical(_wire_request(compares, puts))
    compare_count = len(compares)
    put_count = len(puts)
    operations = compare_count + put_count
    wire_bytes = len(wire)
    budgeted_bytes = wire_bytes + margin
    return {
        "compare_count": compare_count,
        "put_count": put_count,
        "conservative_compare_plus_put_count": operations,
        "compact_gateway_json_body_bytes": wire_bytes,
        "wire_safety_margin_bytes": margin,
        "budgeted_bytes": budgeted_bytes,
        "fits": operations <= max_txn_ops and budgeted_bytes <= max_txn_bytes,
        "operation_budget_fits": operations <= max_txn_ops,
        "byte_budget_fits": budgeted_bytes <= max_txn_bytes,
    }


def _checkpoint(
    *,
    plan_sha256: str,
    next_batch_index: int,
    completed_request_count: int,
    last_batch_sha256: str | None,
) -> dict[str, Any]:
    return {
        "format": CHECKPOINT_FORMAT,
        "plan_sha256": plan_sha256,
        "next_batch_index": next_batch_index,
        "completed_request_count": completed_request_count,
        "last_batch_sha256": last_batch_sha256,
    }


def _batch_digest(pairs: list[tuple[bytes, bytes]]) -> str:
    return _sha256(_json_bytes([
        {"key": key.decode("ascii"), "value_sha256": _sha256(value), "value_bytes": len(value)}
        for key, value in pairs
    ]))


def build_staged_import_plan(
    candidate: dict[str, Any],
    namespace_prefix: bytes,
    *,
    max_txn_ops: int,
    max_txn_bytes: int,
    wire_safety_margin_bytes: int = 4096,
) -> dict[str, Any]:
    """Create deterministic, read-only staging/checkpoint/publish transaction plans."""
    try:
        prefix = validate_isolated_namespace(namespace_prefix)
    except MigrationNamespaceError as exc:
        raise StagedImportPlanError(f"unsafe target namespace: {exc}") from exc
    if prefix == PRODUCTION_PREFIX:
        raise StagedImportPlanError("production namespace is never a staging target")
    max_ops = _required_int(max_txn_ops, "max_txn_ops", 1)
    max_bytes = _required_int(max_txn_bytes, "max_txn_bytes", 1)
    margin = _required_int(wire_safety_margin_bytes, "wire_safety_margin_bytes")

    try:
        state, request_pairs = _validate_candidate(candidate)
    except Exception as exc:
        raise StagedImportPlanError(f"candidate validation failed: {exc}") from exc

    state_key = prefix + b"scheduler/state"
    leader_key = prefix + b"coordinator/leader"
    request_pairs = [(prefix + key, value) for key, value in request_pairs]
    state_value = _canonical(state)
    state_sha = _sha256(state_value)
    request_write_set = [
        {"key": key.decode("ascii"), "value_sha256": _sha256(value), "value_bytes": len(value)}
        for key, value in request_pairs
    ]
    request_set_sha = _sha256(_json_bytes(request_write_set))
    plan_material = {
        "candidate_digest_sha256": candidate["candidate_digest_sha256"],
        "namespace_prefix": prefix.decode("ascii"),
        "scheduler_state_sha256": state_sha,
        "request_write_set_sha256": request_set_sha,
    }
    plan_sha = _sha256(_json_bytes(plan_material))
    checkpoint_key = (
        prefix + b"staging/sqlite-import/"
        + candidate["candidate_digest_sha256"].encode("ascii")
        + b"/checkpoint"
    )
    initial_checkpoint = _checkpoint(
        plan_sha256=plan_sha,
        next_batch_index=0,
        completed_request_count=0,
        last_batch_sha256=None,
    )
    initial_checkpoint_value = _canonical(initial_checkpoint)

    # Initialization claims a unique checkpoint while guarding both publish keys.
    initialize_compares = [
        _version_zero_compare(checkpoint_key),
        _version_zero_compare(state_key),
        _version_zero_compare(leader_key),
    ]
    initialize_puts = [(checkpoint_key, initial_checkpoint_value)]
    initialize_budget = _budget(
        initialize_compares, initialize_puts,
        max_txn_ops=max_ops, max_txn_bytes=max_bytes, margin=margin,
    )
    if not initialize_budget["fits"]:
        raise StagedImportPlanError(
            "checkpoint initialization Txn exceeds the supplied operation/byte budget"
        )

    batches: list[dict[str, Any]] = []
    current_pairs: list[tuple[bytes, bytes]] = []
    previous_checkpoint = initial_checkpoint
    previous_checkpoint_value = initial_checkpoint_value
    completed = 0

    def make_batch(pairs: list[tuple[bytes, bytes]]) -> tuple[dict[str, Any], bytes, dict[str, Any], list[dict[str, Any]], list[tuple[bytes, bytes]]]:
        batch_index = len(batches)
        digest = _batch_digest(pairs)
        next_completed = completed + len(pairs)
        next_checkpoint = _checkpoint(
            plan_sha256=plan_sha,
            next_batch_index=batch_index + 1,
            completed_request_count=next_completed,
            last_batch_sha256=digest,
        )
        next_checkpoint_value = _canonical(next_checkpoint)
        compares = [
            *(_version_zero_compare(key) for key, _ in pairs),
            _value_compare(checkpoint_key, previous_checkpoint_value),
            _version_zero_compare(state_key),
            _version_zero_compare(leader_key),
        ]
        puts = [*pairs, (checkpoint_key, next_checkpoint_value)]
        budget = _budget(
            compares, puts, max_txn_ops=max_ops, max_txn_bytes=max_bytes, margin=margin
        )
        descriptor = {
            "batch_index": batch_index,
            "request_count": len(pairs),
            "request_keys": [key.decode("ascii") for key, _ in pairs],
            "request_value_sha256": [_sha256(value) for _, value in pairs],
            "batch_write_set_sha256": digest,
            "checkpoint_before_sha256": _sha256(previous_checkpoint_value),
            "checkpoint_after_sha256": _sha256(next_checkpoint_value),
            "checkpoint_after": next_checkpoint,
            "budget": budget,
        }
        return descriptor, next_checkpoint_value, next_checkpoint, compares, puts

    for pair in request_pairs:
        tentative = current_pairs + [pair]
        descriptor, next_value, next_checkpoint, compares, puts = make_batch(tentative)
        if descriptor["budget"]["fits"]:
            current_pairs = tentative
            continue
        if not current_pairs:
            raise StagedImportPlanError(
                "one terminal request index cannot fit in a checkpointed batch under the supplied budget"
            )
        # Flush the largest preceding batch and retry this record as a new batch.
        descriptor, next_value, next_checkpoint, compares, puts = make_batch(current_pairs)
        if not descriptor["budget"]["fits"]:
            raise StagedImportPlanError("internal batch segmentation exceeded its computed budget")
        batches.append(descriptor)
        completed += len(current_pairs)
        previous_checkpoint = next_checkpoint
        previous_checkpoint_value = next_value
        current_pairs = [pair]
        descriptor, next_value, next_checkpoint, compares, puts = make_batch(current_pairs)
        if not descriptor["budget"]["fits"]:
            raise StagedImportPlanError(
                "one terminal request index cannot fit in a checkpointed batch under the supplied budget"
            )

    if current_pairs:
        descriptor, next_value, next_checkpoint, compares, puts = make_batch(current_pairs)
        if not descriptor["budget"]["fits"]:
            raise StagedImportPlanError("final checkpointed batch exceeds the supplied budget")
        batches.append(descriptor)
        completed += len(current_pairs)
        previous_checkpoint = next_checkpoint
        previous_checkpoint_value = next_value

    if completed != len(request_pairs):
        raise StagedImportPlanError("internal checkpoint plan does not cover every request index")

    # Scheduler state is the publish marker for this existing runtime schema.
    publish_compares = [
        _value_compare(checkpoint_key, previous_checkpoint_value),
        _version_zero_compare(state_key),
        _version_zero_compare(leader_key),
    ]
    publish_puts = [(state_key, state_value)]
    publish_budget = _budget(
        publish_compares, publish_puts,
        max_txn_ops=max_ops, max_txn_bytes=max_bytes, margin=margin,
    )
    if not publish_budget["fits"]:
        raise StagedImportPlanError(
            "scheduler aggregate cannot fit in the final single-key publish Txn; "
            "the schema/runtime must be redesigned before staging"
        )

    return {
        "format": FORMAT,
        "candidate_digest_sha256": candidate["candidate_digest_sha256"],
        "source_snapshot_digest_sha256": candidate["source_snapshot_digest_sha256"],
        "plan_sha256": plan_sha,
        "target": {
            "namespace_prefix": prefix.decode("ascii"),
            "checkpoint_key": checkpoint_key.decode("ascii"),
            "scheduler_state_key": state_key.decode("ascii"),
            "leader_key_compare_only": leader_key.decode("ascii"),
            "application_access_must_remain_disabled_until_publish_verified": True,
            "production_write_allowed": False,
        },
        "strategy": {
            "request_indexes_are_written_in_bounded_atomic_batches": True,
            "checkpoint_advances_in_same_txn_as_each_batch": True,
            "scheduler_state_is_written_only_in_final_publish_txn": True,
            "leader_ttl_key_is_never_imported": True,
            "active_admission_leases_and_waiters_imported": 0,
            "native_lease_grants_during_staging": 0,
            "staging_checkpoint_retained_for_audit_until_post_import_acceptance": True,
            "single_scheduler_state_value_must_fit_one_txn": True,
        },
        "transactions": {
            "initialize_checkpoint": {
                "transaction_count": 1,
                "budget": initialize_budget,
                "checkpoint_sha256": _sha256(initial_checkpoint_value),
                "checkpoint_value": initial_checkpoint,
            },
            "request_batches": batches,
            "publish_scheduler_state": {
                "transaction_count": 1,
                "budget": publish_budget,
                "scheduler_state_value_bytes": len(state_value),
                "scheduler_state_sha256": state_sha,
                "checkpoint_sha256": _sha256(previous_checkpoint_value),
            },
            "total_transaction_count": 2 + len(batches),
            "total_request_indexes": len(request_pairs),
        },
        "recovery_protocol": {
            "before_each_batch": "linearizable read checkpoint and require exact expected predecessor; verify destination keys absent",
            "after_unknown_batch_txn": (
                "linearizable read checkpoint and every key in that batch; COMMITTED only when checkpoint "
                "belongs to this plan and has advanced through the batch and all batch values match; "
                "retry only when checkpoint equals predecessor and all batch keys are absent; otherwise quarantine"
            ),
            "after_unknown_publish_txn": (
                "linearizable read scheduler state, checkpoint and Leader key; COMMITTED only when state bytes "
                "match candidate, checkpoint is complete and Leader key absent; retry only when state is absent "
                "and checkpoint is complete; otherwise quarantine"
            ),
            "partial_batch_write_is_not_a_valid_etcd_txn_outcome": True,
            "unknown_lease_grant_is_not_applicable_to_this_quiescent_candidate": True,
        },
        "activation_barrier": [
            "Use a fresh isolated etcd cluster or server-side RBAC that gives only the migration principal access during staging.",
            "Keep all application principals denied access to this namespace; an early Scheduler construction can initialize an empty state and invalidate the import.",
            "Run a linearizable read-back of every terminal request index and the full checkpoint chain before final publication.",
            "Publish scheduler/state only after every batch is committed and verified; do not start the application yet.",
            "Read back scheduler/state and Leader key; only then enable application access and start a single new Coordinator Leader claim.",
            "Keep Provider operations disabled until external Provider fencing floors and scope reconciliation are independently approved.",
        ],
        "non_goals": [
            "This is a read-only protocol model; it includes no etcd client, Range, Txn, Lease, RBAC, credential or application startup action.",
            "It does not implement the actual batch writer or automatic checkpoint resumption.",
            "It does not split the scheduler aggregate; if that single value exceeds a Txn/request budget, schema/runtime redesign is required.",
            "It does not automatically delete checkpoints or staging metadata after activation.",
        ],
        "write_set": {
            "scheduler_state_value_bytes": len(state_value),
            "scheduler_state_sha256": state_sha,
            "terminal_request_count": len(request_pairs),
            "terminal_request_write_set_sha256": request_set_sha,
            "checkpoint_value_bytes": len(initial_checkpoint_value),
            "terminal_request_value_bytes": sum(len(value) for _, value in request_pairs),
        },
    }


def classify_checkpoint_initialization_unknown(
    *,
    observed_checkpoint: bytes | None,
    observed_state_exists: bool,
    observed_leader_exists: bool,
    observed_request_key_count: int,
    expected_initial_checkpoint: bytes,
) -> str:
    if observed_state_exists or observed_leader_exists or observed_request_key_count:
        return UNKNOWN_QUARANTINE
    if observed_checkpoint == expected_initial_checkpoint:
        return UNKNOWN_COMMITTED
    if observed_checkpoint is None:
        return UNKNOWN_RETRY
    return UNKNOWN_QUARANTINE


def classify_batch_unknown(
    *,
    plan_sha256: str,
    expected_previous_checkpoint: bytes,
    observed_checkpoint: bytes | None,
    expected_completed_request_count: int,
    observed_request_values: Mapping[bytes, bytes | None],
    expected_request_values: Mapping[bytes, bytes],
    observed_state_exists: bool,
    observed_leader_exists: bool,
) -> str:
    if observed_state_exists or observed_leader_exists:
        return UNKNOWN_QUARANTINE
    if set(observed_request_values) != set(expected_request_values):
        return UNKNOWN_QUARANTINE
    if (
        observed_checkpoint == expected_previous_checkpoint
        and all(value is None for value in observed_request_values.values())
    ):
        return UNKNOWN_RETRY
    if observed_checkpoint is None:
        return UNKNOWN_QUARANTINE
    try:
        checkpoint = json.loads(observed_checkpoint.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return UNKNOWN_QUARANTINE
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("format") != CHECKPOINT_FORMAT
        or checkpoint.get("plan_sha256") != plan_sha256
        or not isinstance(checkpoint.get("next_batch_index"), int)
        or not isinstance(checkpoint.get("completed_request_count"), int)
        or checkpoint["completed_request_count"] < expected_completed_request_count
        or checkpoint["next_batch_index"] < 1
    ):
        return UNKNOWN_QUARANTINE
    if all(
        observed_request_values[key] == expected_request_values[key]
        for key in expected_request_values
    ):
        return UNKNOWN_COMMITTED
    return UNKNOWN_QUARANTINE


def classify_publish_unknown(
    *,
    observed_checkpoint: bytes | None,
    expected_final_checkpoint: bytes,
    observed_state: bytes | None,
    expected_state: bytes,
    observed_leader_exists: bool,
) -> str:
    if observed_leader_exists:
        return UNKNOWN_QUARANTINE
    if observed_checkpoint != expected_final_checkpoint:
        return UNKNOWN_QUARANTINE
    if observed_state == expected_state:
        return UNKNOWN_COMMITTED
    if observed_state is None:
        return UNKNOWN_RETRY
    return UNKNOWN_QUARANTINE


def _write_private_json(path: Path, payload: Any) -> None:
    destination = path.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    fd, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=str(destination.parent)
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only checkpointed Unified schema-v2 staged import protocol"
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--max-txn-ops", required=True, type=int)
    parser.add_argument("--max-txn-bytes", required=True, type=int)
    parser.add_argument("--wire-safety-margin-bytes", type=int, default=4096)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with args.candidate.expanduser().open("r", encoding="utf-8") as stream:
            candidate = json.load(stream)
        plan = build_staged_import_plan(
            candidate,
            args.namespace.encode("ascii"),
            max_txn_ops=args.max_txn_ops,
            max_txn_bytes=args.max_txn_bytes,
            wire_safety_margin_bytes=args.wire_safety_margin_bytes,
        )
        _write_private_json(args.output, plan)
    except (
        OSError, UnicodeDecodeError, json.JSONDecodeError, UnicodeEncodeError,
        StagedImportPlanError, ValueError,
    ) as exc:
        parser.exit(2, f"error: {exc}\n")
    summary = {
        "status": "PROTOCOL_READY",
        "plan_sha256": plan["plan_sha256"],
        "namespace_prefix": plan["target"]["namespace_prefix"],
        "terminal_request_count": plan["transactions"]["total_request_indexes"],
        "request_batch_count": len(plan["transactions"]["request_batches"]),
        "total_transaction_count": plan["transactions"]["total_transaction_count"],
        "output": str(args.output.expanduser().resolve()),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

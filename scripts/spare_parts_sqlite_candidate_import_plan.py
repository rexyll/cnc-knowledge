#!/usr/bin/env python3
"""Build a read-only, single-Txn import plan for a Unified schema-v2 candidate.

The plan contains no etcd connection or write path. It estimates one atomic Txn
that creates the scheduler aggregate and all terminal request indexes while
comparing every destination key as absent. Oversized candidates are rejected;
this tool never silently converts the operation into a multi-Txn import.
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
from typing import Any

from scripts.spare_parts_migration_namespace import (
    MigrationNamespaceError,
    validate_isolated_namespace,
)
from scripts.spare_parts_provider_unified_admission_store import (
    StoreBackedProviderAdmissionCoordinator,
)
from scripts.spare_parts_sqlite_migration_inventory import _json_bytes


class ImportPlanError(RuntimeError):
    """Raised when a candidate cannot be safely planned for schema-v2."""


FORMAT = "ch17-sqlite-unified-import-plan-v1"
CANDIDATE_FORMAT = "ch17-sqlite-unified-candidate-v1"
PRODUCTION_PREFIX = b"/cnc/admission/unified/v2/"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ImportPlanError("candidate contains non-canonical JSON values") from exc


def _required_int(value: Any, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ImportPlanError(f"{name} must be an integer >= {minimum}")
    return value


def _finite_number(value: Any, name: str) -> float:
    if (
        not isinstance(value, (int, float)) or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ImportPlanError(f"{name} must be a finite number")
    return float(value)


def _request_key(request_id: str) -> str:
    digest = _sha256(request_id.encode("utf-8"))
    return "requests/" + digest


def _validate_candidate(candidate: Any) -> tuple[dict[str, Any], list[tuple[bytes, bytes]]]:
    if not isinstance(candidate, dict) or candidate.get("format") != CANDIDATE_FORMAT:
        raise ImportPlanError("unsupported candidate bundle format")
    required = {
        "format", "source_snapshot_digest_sha256", "generated_at_unix", "target",
        "state_template", "terminal_request_indexes", "recovery_requirements",
        "legacy_metadata", "counts", "candidate_digest_sha256",
    }
    if set(candidate) != required:
        raise ImportPlanError("candidate top-level schema mismatch")

    supplied_digest = candidate.get("candidate_digest_sha256")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        raise ImportPlanError("candidate digest is missing or malformed")
    digest_material = dict(candidate)
    digest_material.pop("candidate_digest_sha256")
    if _sha256(_json_bytes(digest_material)) != supplied_digest:
        raise ImportPlanError("candidate digest does not verify")

    source_digest = candidate.get("source_snapshot_digest_sha256")
    if not isinstance(source_digest, str) or len(source_digest) != 64:
        raise ImportPlanError("source snapshot digest is missing or malformed")
    int(source_digest, 16)
    _finite_number(candidate.get("generated_at_unix"), "generated_at_unix")

    target = candidate.get("target")
    if (
        not isinstance(target, dict)
        or target.get("namespace") is not None
        or target.get("namespace_must_be_explicit") is not True
        or target.get("mode") != "ISOLATED_CANDIDATE_ONLY"
        or target.get("requires_empty_namespace") is not True
        or target.get("production_write_allowed") is not False
    ):
        raise ImportPlanError("candidate target safety contract is invalid")

    state = candidate.get("state_template")
    if not isinstance(state, dict):
        raise ImportPlanError("candidate state_template must be an object")
    try:
        StoreBackedProviderAdmissionCoordinator._validate_state(state)
    except Exception as exc:
        raise ImportPlanError(f"candidate state does not match Unified schema-v2: {exc}") from exc
    if state.get("active") != {} or state.get("waiters") != []:
        raise ImportPlanError("candidate must not contain active leases or waiters")
    coordinator = state.get("coordinator", {})
    if coordinator.get("leader") is not None:
        raise ImportPlanError("legacy Leader must not be imported")
    if not isinstance(state.get("next_fencing_token"), int) or isinstance(
        state.get("next_fencing_token"), bool
    ):
        raise ImportPlanError("candidate global fencing floor is invalid")

    scopes = coordinator.get("scopes", {})
    operations = coordinator.get("operations", {})
    if not isinstance(scopes, dict) or not isinstance(operations, dict):
        raise ImportPlanError("candidate Coordinator maps are malformed")
    for scope_name, scope in scopes.items():
        if not isinstance(scope_name, str) or not scope_name or not isinstance(scope, dict):
            raise ImportPlanError("candidate contains an invalid Coordinator scope")
        if set(scope) != {
            "high_water_token", "lease_id", "owner_id", "tenant_id", "domain",
            "lease_expires_at", "lease_state", "latest_operation_sequence",
            "provider_generation", "updated_at",
        }:
            raise ImportPlanError(f"Coordinator scope schema mismatch: {scope_name}")
        _required_int(scope.get("high_water_token"), f"{scope_name}.high_water_token")
        _required_int(
            scope.get("latest_operation_sequence"),
            f"{scope_name}.latest_operation_sequence",
        )
        _finite_number(scope.get("updated_at"), f"{scope_name}.updated_at")
        if scope.get("lease_state") not in {"IDLE", "RECOVERY_REQUIRED"}:
            raise ImportPlanError(f"scope {scope_name} is not safely quiescent")
        if any(scope.get(field) is not None for field in (
            "lease_id", "owner_id", "tenant_id", "domain", "lease_expires_at"
        )):
            raise ImportPlanError(f"scope {scope_name} unexpectedly contains a live lease identity")

    operation_states = {
        "PENDING_ACTIVATION", "ACTIVE", "REVOKING", "REVOKED",
        "PENDING_PUBLISH", "COMMITTED", "RECOVERY_REVIEW",
    }
    for operation_key, operation in operations.items():
        if not isinstance(operation_key, str) or not isinstance(operation, dict):
            raise ImportPlanError("candidate contains an invalid Coordinator operation")
        expected_key = _sha256((
            str(operation.get("scope", "")) + "\x00"
            + str(operation.get("idempotency_key", ""))
        ).encode("utf-8"))
        if operation_key != expected_key:
            raise ImportPlanError("Coordinator operation map key is not deterministic")
        if operation.get("scope") not in scopes or operation.get("state") not in operation_states:
            raise ImportPlanError("Coordinator operation references an invalid scope or state")
        if not isinstance(operation.get("request_sha256"), str) or len(
            operation["request_sha256"]
        ) != 64:
            raise ImportPlanError("Coordinator operation request digest is malformed")
        int(operation["request_sha256"], 16)
        _required_int(operation.get("fencing_token"), "operation fencing_token")
        if operation.get("operation_sequence") is not None:
            _required_int(operation["operation_sequence"], "operation_sequence")
        _finite_number(operation.get("lease_expires_at"), "operation.lease_expires_at")
        _finite_number(operation.get("created_at"), "operation.created_at")
        _finite_number(operation.get("updated_at"), "operation.updated_at")
        manifest_hash = operation.get("manifest_sha256")
        if manifest_hash is not None:
            if not isinstance(manifest_hash, str) or len(manifest_hash) != 64:
                raise ImportPlanError("Coordinator operation manifest digest is malformed")
            int(manifest_hash, 16)
        scope = scopes[operation["scope"]]
        if scope["high_water_token"] < operation["fencing_token"]:
            raise ImportPlanError("scope fencing high-water is below operation history")
        sequence = operation.get("operation_sequence")
        if sequence is not None and scope["latest_operation_sequence"] < sequence:
            raise ImportPlanError("scope operation sequence floor is below operation history")

    recovery = candidate.get("recovery_requirements")
    if (
        not isinstance(recovery, dict)
        or recovery.get("leader_must_be_reclaimed") is not True
        or recovery.get("external_fencing_reconciliation") != "REQUIRED"
        or recovery.get("external_fencing_floor") is not None
        or recovery.get("active_lease_ttl_keys_are_not_imported") is not True
        or recovery.get("terminal_request_backend_lease_id_sentinel") != 1
        or recovery.get("terminal_request_backend_lease_id_is_not_a_live_lease") is not True
    ):
        raise ImportPlanError("candidate recovery requirements do not preserve safety barriers")
    _required_int(recovery.get("leader_epoch_floor"), "leader_epoch_floor")

    indexes = candidate.get("terminal_request_indexes")
    if not isinstance(indexes, list):
        raise ImportPlanError("terminal_request_indexes must be a list")
    request_pairs: list[tuple[bytes, bytes]] = []
    seen_ids: set[str] = set()
    seen_keys: set[bytes] = set()
    max_request_token = 0
    for index, item in enumerate(indexes):
        if not isinstance(item, dict) or set(item) != {"key", "record"}:
            raise ImportPlanError(f"terminal request index {index} schema mismatch")
        record = item["record"]
        if not isinstance(record, dict) or not StoreBackedProviderAdmissionCoordinator._record_schema(record):
            raise ImportPlanError(f"terminal request index {index} does not match Unified request schema")
        if record["state"] not in {"RELEASED", "EXPIRED"} or record["backend_lease_id"] != 1:
            raise ImportPlanError("only terminal records with the reserved non-Lease sentinel are allowed")
        request_id = record["request_id"]
        if request_id in seen_ids:
            raise ImportPlanError(f"duplicate terminal request ID: {request_id}")
        seen_ids.add(request_id)
        expected_key = _request_key(request_id)
        if item["key"] != expected_key:
            raise ImportPlanError("terminal request key does not match the Unified request-key derivation")
        key = item["key"].encode("ascii")
        if key in seen_keys:
            raise ImportPlanError("terminal request index key collision")
        seen_keys.add(key)
        value = _canonical_json(record)
        request_pairs.append((key, value))
        max_request_token = max(max_request_token, record["fencing_token"])

    if state["next_fencing_token"] < max_request_token:
        raise ImportPlanError("global Admission fencing floor is below terminal request history")
    counts = candidate.get("counts")
    expected_counts = {
        "terminal_requests": len(indexes),
        "scopes": len(scopes),
        "operations": len(operations),
        "active_leases": 0,
        "waiters": 0,
        "pending_operations": 0,
    }
    if counts != expected_counts:
        raise ImportPlanError("candidate counts do not match the actual state and indexes")
    return state, sorted(request_pairs, key=lambda pair: pair[0])


def build_import_plan(
    candidate: dict[str, Any],
    namespace_prefix: bytes,
    *,
    max_txn_ops: int,
    max_txn_bytes: int,
    wire_safety_margin_bytes: int = 4096,
) -> dict[str, Any]:
    """Return a deterministic one-shot Txn plan; never connect to a store."""
    try:
        prefix = validate_isolated_namespace(namespace_prefix)
    except MigrationNamespaceError as exc:
        raise ImportPlanError(f"unsafe target namespace: {exc}") from exc
    if prefix == PRODUCTION_PREFIX:
        raise ImportPlanError("production namespace is never an import target")
    max_ops = _required_int(max_txn_ops, "max_txn_ops", 1)
    max_bytes = _required_int(max_txn_bytes, "max_txn_bytes", 1)
    margin = _required_int(wire_safety_margin_bytes, "wire_safety_margin_bytes")

    state, request_pairs = _validate_candidate(candidate)
    state_key = prefix + b"scheduler/state"
    leader_key = prefix + b"coordinator/leader"
    put_pairs = [(state_key, _canonical_json(state))] + [
        (prefix + key, value) for key, value in request_pairs
    ]
    if len({key for key, _ in put_pairs}) != len(put_pairs):
        raise ImportPlanError("planned destination key collision")

    compare_keys = sorted([key for key, _ in put_pairs] + [leader_key])
    if len(set(compare_keys)) != len(compare_keys):
        raise ImportPlanError("destination compare key collision")

    compare_requests = [
        {
            "key": base64.b64encode(key).decode("ascii"),
            "target": "VERSION",
            "result": "EQUAL",
            "version": "0",
        }
        for key in compare_keys
    ]
    success_requests = [
        {
            "request_put": {
                "key": base64.b64encode(key).decode("ascii"),
                "value": base64.b64encode(value).decode("ascii"),
            }
        }
        for key, value in put_pairs
    ]
    wire_request = {
        "compare": compare_requests,
        "success": success_requests,
        "failure": [],
    }
    wire_bytes = len(json.dumps(
        wire_request, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"))
    estimated_with_margin = wire_bytes + margin
    compare_count = len(compare_requests)
    put_count = len(success_requests)
    conservative_operation_count = compare_count + put_count
    fits_ops = conservative_operation_count <= max_ops
    fits_bytes = estimated_with_margin <= max_bytes
    reasons = []
    if not fits_ops:
        reasons.append(
            f"conservative compare+put count {conservative_operation_count} exceeds budget {max_ops}"
        )
    if not fits_bytes:
        reasons.append(
            f"estimated compact gateway body plus margin {estimated_with_margin} bytes exceeds budget {max_bytes} bytes"
        )

    key_bytes = sum(len(key) for key, _ in put_pairs)
    value_bytes = sum(len(value) for _, value in put_pairs)
    return {
        "format": FORMAT,
        "candidate_digest_sha256": candidate["candidate_digest_sha256"],
        "source_snapshot_digest_sha256": candidate["source_snapshot_digest_sha256"],
        "target": {
            "namespace_prefix": prefix.decode("ascii"),
            "scheduler_state_key": state_key.decode("ascii"),
            "leader_key_compare_only": leader_key.decode("ascii"),
            "leader_key_must_remain_absent_until_new_claim": True,
            "production_write_allowed": False,
        },
        "atomicity": {
            "transaction_count": 1,
            "compare_count": compare_count,
            "put_count": put_count,
            "delete_count": 0,
            "conservative_compare_plus_put_count": conservative_operation_count,
            "all_destination_keys_compared_as_version_zero": True,
            "state_and_terminal_indexes_commit_together": True,
            "legacy_leader_ttl_key_imported": False,
            "native_lease_grants_required_for_import": 0,
        },
        "payload_estimate": {
            "scheduler_state_value_bytes": len(put_pairs[0][1]),
            "terminal_request_count": len(request_pairs),
            "terminal_request_value_bytes": sum(len(value) for _, value in request_pairs),
            "destination_key_bytes_written": key_bytes,
            "value_bytes_written": value_bytes,
            "compact_etcd_gateway_json_body_bytes": wire_bytes,
            "wire_safety_margin_bytes": margin,
            "budgeted_bytes": estimated_with_margin,
            "budget_is_conservative_operator_input_not_discovered_server_configuration": True,
        },
        "limits": {
            "max_txn_ops": max_ops,
            "max_txn_bytes": max_bytes,
            "fits": fits_ops and fits_bytes,
            "reasons": reasons,
        },
        "write_set_digest_sha256": _sha256(_json_bytes([
            {"key": key.decode("ascii"), "value_sha256": _sha256(value), "value_bytes": len(value)}
            for key, value in put_pairs
        ])),
        "write_set": [
            {
                "key": key.decode("ascii"),
                "value_sha256": _sha256(value),
                "value_bytes": len(value),
            }
            for key, value in put_pairs
        ],
        "preconditions": [
            "A fresh, isolated etcd cluster or server-side RBAC must exclude concurrent writers.",
            "A linearizable empty-prefix preflight must be repeated immediately before this Txn.",
            "The exact cluster identity, principal identity, preflight revision and namespace ID must be recorded.",
            "Application credentials must remain unable to access this namespace until the Txn commits and post-write verification passes.",
            "External Provider fencing floors must be reconciled and approved before any Provider operation is enabled.",
            "A new Coordinator Leader must be claimed after import; the legacy Leader TTL key is never restored.",
        ],
        "not_performed": [
            "No etcd connection or Range was performed by this planner.",
            "No KV, Lease, RBAC, credential or production authority was created, modified or revoked.",
            "No automatic multi-transaction batching or checkpoint protocol is implemented.",
        ],
    }


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
        description="Build a read-only single-Txn Unified schema-v2 candidate import plan"
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--namespace", required=True, help="isolated /cnc/migration/isolated/{id}/ prefix")
    parser.add_argument("--max-txn-ops", required=True, type=int, help="conservative compare+put budget")
    parser.add_argument("--max-txn-bytes", required=True, type=int, help="operator-supplied Txn request byte budget")
    parser.add_argument("--wire-safety-margin-bytes", type=int, default=4096)
    parser.add_argument("--output", required=True, type=Path, help="private plan JSON output")
    args = parser.parse_args(argv)
    try:
        with args.candidate.expanduser().open("r", encoding="utf-8") as stream:
            candidate = json.load(stream)
        plan = build_import_plan(
            candidate, args.namespace.encode("ascii"),
            max_txn_ops=args.max_txn_ops,
            max_txn_bytes=args.max_txn_bytes,
            wire_safety_margin_bytes=args.wire_safety_margin_bytes,
        )
        _write_private_json(args.output, plan)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, UnicodeEncodeError, ImportPlanError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps({
        "status": "PLAN_READY" if plan["limits"]["fits"] else "CAPACITY_EXCEEDED",
        "candidate_digest_sha256": plan["candidate_digest_sha256"],
        "namespace_prefix": plan["target"]["namespace_prefix"],
        "terminal_requests": plan["payload_estimate"]["terminal_request_count"],
        "compare_count": plan["atomicity"]["compare_count"],
        "put_count": plan["atomicity"]["put_count"],
        "budgeted_bytes": plan["payload_estimate"]["budgeted_bytes"],
        "limits": plan["limits"],
        "output": str(args.output.expanduser().resolve()),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if plan["limits"]["fits"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

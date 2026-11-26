#!/usr/bin/env python3
"""Offline capacity probe for the unified spare-parts Coordinator aggregate.

The probe measures the repository's canonical JSON value exactly. It does not
estimate serialized gRPC/protobuf request size, call a store, or contact etcd.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

from scripts.spare_parts_provider_unified_admission_store import (
    StoreBackedProviderAdmissionCoordinator,
)
from scripts.spare_parts_provider_unified_coordinator_authority import (
    StoreBackedCoordinatorAuthority,
)

DEFAULT_ETCD_MAX_REQUEST_BYTES = 1_572_864
DEFAULT_TARGET_UTILIZATION = 0.50
MAX_SYNTHETIC_ITEMS = 100_000
DEFAULT_MATRIX = (
    Path(__file__).resolve().parents[1]
    / "resouces"
    / "17-operation-maintenance-and-repair"
    / "spare-parts-coordinator-capacity-profile-v1.csv"
)


def _count(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    if value > MAX_SYNTHETIC_ITEMS:
        raise ValueError(f"{field} exceeds the synthetic probe safety ceiling")
    return value


def build_synthetic_state(
    *,
    scope_count: int,
    operations_per_scope: int,
    active_lease_count: int = 0,
    waiter_count: int = 0,
) -> dict[str, Any]:
    """Build a deterministic schema-v2 aggregate using current record shapes."""
    scopes_n = _count(scope_count, "scope_count")
    operations_n = _count(operations_per_scope, "operations_per_scope")
    active_n = _count(active_lease_count, "active_lease_count")
    waiters_n = _count(waiter_count, "waiter_count")
    if operations_n and not scopes_n:
        raise ValueError("operations_per_scope requires at least one scope")
    if scopes_n * operations_n > MAX_SYNTHETIC_ITEMS:
        raise ValueError("total synthetic operations exceeds the probe safety ceiling")

    scheduler = StoreBackedProviderAdmissionCoordinator
    authority = StoreBackedCoordinatorAuthority
    state = scheduler._initial_state(
        "0" * 64,
        {"read": 4, "write": 2, "multipart": 2, "inventory": 1},
        {},
        max(256, waiters_n),
        1.0,
    )
    now = 1_800_000_000.0
    scope_names: list[str] = []

    for index in range(scopes_n):
        tenant = f"synthetic-tenant-{index:06d}"
        scope = f"tenants/{tenant}/cnc/spares/scope-{index:06d}"
        scope_names.append(scope)
        state["coordinator"]["scopes"][scope] = authority._default_scope(
            scope, now
        )

    for operation_index in range(scopes_n * operations_n):
        scope_index = operation_index % scopes_n
        scope = scope_names[scope_index]
        tenant = f"synthetic-tenant-{scope_index:06d}"
        owner = f"synthetic-owner-{scope_index:06d}"
        sequence = operation_index // scopes_n + 1
        idempotency_key = f"publish-{operation_index:08d}"
        payload_label = f"{scope}:{idempotency_key}"
        lease_values = {
            "lease_id": f"scope-lease-{scope_index:08d}",
            "owner_id": owner,
            "tenant_id": tenant,
            "domain": "write",
            "lease_expires_at": now + 3_600,
        }
        record = authority._record_from_operation(
            scope=scope,
            kind="PUBLISH",
            idempotency_key=idempotency_key,
            request_sha256=hashlib.sha256(
                ("request:" + payload_label).encode("utf-8")
            ).hexdigest(),
            fencing_token=scope_index + 1,
            operation_sequence=sequence,
            lease_values=lease_values,
            state="COMMITTED",
            provider_generation=f"generation-{operation_index:08d}",
            now=now,
            manifest_key=f"{scope}/manifests/{operation_index:08d}.json",
            manifest_sha256=hashlib.sha256(
                ("manifest:" + payload_label).encode("utf-8")
            ).hexdigest(),
        )
        authority._put_operation(state["coordinator"]["operations"], record)
        scope_record = state["coordinator"]["scopes"][scope]
        scope_record.update(
            {
                "high_water_token": scope_index + 1,
                "lease_id": lease_values["lease_id"],
                "owner_id": owner,
                "tenant_id": tenant,
                "domain": "write",
                "lease_expires_at": now + 3_600,
                "lease_state": "ACTIVE",
                "latest_operation_sequence": sequence,
                "provider_generation": f"generation-{operation_index:08d}",
            }
        )

    for index in range(active_n):
        tenant = f"synthetic-tenant-{index % max(1, scopes_n):06d}"
        request_id = f"request-{index:08d}"
        lease_id = f"admission-lease-{index:08d}"
        state["active"][lease_id] = {
            "request_id": request_id,
            "lease_id": lease_id,
            "owner_id": f"admission-owner-{index:08d}",
            "task_id": f"task-{index:08d}",
            "tenant_id": tenant,
            "domain": "write",
            "fencing_token": index + 1,
            "expires_at": now + 3_600,
            "state": "ACTIVE",
            "backend_lease_id": index + 1,
        }
    state["next_fencing_token"] = active_n
    state["counters"]["issued_leases"] = active_n

    for index in range(waiters_n):
        tenant = f"synthetic-tenant-{index % max(1, scopes_n):06d}"
        state["waiters"].append(
            {
                "request_id": f"waiter-request-{index:08d}",
                "owner_id": f"waiter-owner-{index:08d}",
                "task_id": f"waiter-task-{index:08d}",
                "tenant_id": tenant,
                "domain": "write",
                "priority": index % 10,
                "sequence": index + 1,
                "queued_at": now,
                "expires_at": now + 600,
            }
        )
    state["next_waiter_sequence"] = waiters_n

    scheduler._validate_state(state)
    for record in state["active"].values():
        if not scheduler._record_schema(record):
            raise AssertionError("synthetic active lease does not match scheduler schema")
    for scope in state["coordinator"]["scopes"]:
        authority._ensure_scope(state["coordinator"]["scopes"], scope, now)
    for key, record in state["coordinator"]["operations"].items():
        expected = authority._op_key(record["scope"], record["idempotency_key"])
        if key != expected or record["state"] not in authority._OP_STATES:
            raise AssertionError("synthetic operation index or state is malformed")
    return state


def inspect_aggregate(
    state: dict[str, Any],
    *,
    max_request_bytes: int = DEFAULT_ETCD_MAX_REQUEST_BYTES,
    target_utilization: float = DEFAULT_TARGET_UTILIZATION,
) -> dict[str, Any]:
    """Measure canonical state bytes and expose explicitly-labelled estimates."""
    if (
        not isinstance(max_request_bytes, int)
        or isinstance(max_request_bytes, bool)
        or max_request_bytes <= 0
    ):
        raise ValueError("max_request_bytes must be a positive integer")
    if (
        not isinstance(target_utilization, (int, float))
        or isinstance(target_utilization, bool)
        or not math.isfinite(target_utilization)
        or not 0 < target_utilization <= 1
    ):
        raise ValueError("target_utilization must be in (0, 1]")

    StoreBackedProviderAdmissionCoordinator._validate_state(state)
    coordinator = state["coordinator"]
    aggregate_bytes = StoreBackedProviderAdmissionCoordinator._encode(state)
    coordinator_bytes = StoreBackedProviderAdmissionCoordinator._encode(coordinator)
    scopes_bytes = StoreBackedProviderAdmissionCoordinator._encode(
        coordinator["scopes"]
    )
    operations_bytes = StoreBackedProviderAdmissionCoordinator._encode(
        coordinator["operations"]
    )
    active_count = len(state["active"])
    target_budget = int(max_request_bytes * float(target_utilization))
    request_ratio = len(aggregate_bytes) / max_request_bytes
    budget_ratio = len(aggregate_bytes) / target_budget if target_budget else None
    operation_count = len(coordinator["operations"])
    operation_record_mean = (
        len(operations_bytes) / operation_count if operation_count else None
    )
    coordinator_compare_estimate = 1 + 2 * active_count + 1

    return {
        "schema_version": state["schema_version"],
        "aggregate_value_bytes": len(aggregate_bytes),
        "coordinator_subtree_bytes": len(coordinator_bytes),
        "scope_index_bytes": len(scopes_bytes),
        "operation_index_bytes": len(operations_bytes),
        "scope_count": len(coordinator["scopes"]),
        "operation_count": operation_count,
        "active_lease_count": active_count,
        "waiter_count": len(state["waiters"]),
        "mean_operation_index_bytes": operation_record_mean,
        "reference_max_request_bytes": max_request_bytes,
        "aggregate_target_utilization": float(target_utilization),
        "aggregate_target_budget_bytes": target_budget,
        "request_value_lower_bound_bytes": len(aggregate_bytes),
        "request_value_to_reference_limit_ratio": request_ratio,
        "target_budget_utilization_ratio": budget_ratio,
        "within_target_budget": len(aggregate_bytes) <= target_budget,
        "coordinator_compare_count_estimate": coordinator_compare_estimate,
        "compare_count_model": (
            "1 aggregate revision compare + 2 exact compares per active "
            "Admission lease/request pair + 1 current Leader compare"
        ),
        "measurement_boundary": (
            "Aggregate JSON value bytes are exact; this is only a lower bound "
            "for the full transaction request. Protobuf/gRPC envelope, key "
            "bytes, and adapter-specific encoding are not measured."
        ),
    }


def run_matrix(
    matrix_path: Path,
    *,
    max_request_bytes: int = DEFAULT_ETCD_MAX_REQUEST_BYTES,
    target_utilization: float = DEFAULT_TARGET_UTILIZATION,
) -> list[dict[str, Any]]:
    required = {
        "scenario_id",
        "purpose",
        "scope_count",
        "operations_per_scope",
        "active_lease_count",
        "waiter_count",
    }
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    with matrix_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("capacity profile matrix is missing required columns")
        for row_number, row in enumerate(reader, start=2):
            scenario_id = (row.get("scenario_id") or "").strip()
            purpose = (row.get("purpose") or "").strip()
            if not scenario_id or scenario_id in seen or not purpose:
                raise ValueError(f"invalid or duplicate scenario metadata at row {row_number}")
            seen.add(scenario_id)
            params = {
                "scope_count": int(row["scope_count"]),
                "operations_per_scope": int(row["operations_per_scope"]),
                "active_lease_count": int(row["active_lease_count"]),
                "waiter_count": int(row["waiter_count"]),
            }
            state = build_synthetic_state(**params)
            result = inspect_aggregate(
                state,
                max_request_bytes=max_request_bytes,
                target_utilization=target_utilization,
            )
            results.append(
                {
                    "scenario_id": scenario_id,
                    "purpose": purpose,
                    "parameters": params,
                    "synthetic_only": True,
                    **result,
                }
            )
    if not results:
        raise ValueError("capacity profile matrix contains no scenarios")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument(
        "--max-request-bytes",
        type=int,
        default=DEFAULT_ETCD_MAX_REQUEST_BYTES,
        help="reference limit only; the etcd server setting is configurable",
    )
    parser.add_argument(
        "--target-utilization",
        type=float,
        default=DEFAULT_TARGET_UTILIZATION,
        help="analytical budget fraction, not a server-enforced limit",
    )
    args = parser.parse_args(argv)
    try:
        report = {
            "probe": "synthetic_unified_coordinator_aggregate_capacity",
            "synthetic_only": True,
            "real_store_accessed": False,
            "real_etcd_accessed": False,
            "reference": {
                "etcd_default_max_request_bytes": DEFAULT_ETCD_MAX_REQUEST_BYTES,
                "configured_reference_max_request_bytes": args.max_request_bytes,
                "target_utilization": args.target_utilization,
            },
            "scenarios": run_matrix(
                args.matrix,
                max_request_bytes=args.max_request_bytes,
                target_utilization=args.target_utilization,
            ),
        }
    except (OSError, ValueError, AssertionError) as exc:
        parser.error(str(exc))
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a verified, quiescent Unified schema-v2 candidate import bundle.

This stage deliberately does not write to etcd or any production authority.
It validates the MIG-03 inventory/records pair, verifies policy identity, and
produces a deterministic candidate state template plus permanent request keys.
Active leases, waiters and unresolved operations must be drained before export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from scripts.spare_parts_sqlite_migration_inventory import ALL_TABLES, _json_bytes


class CandidateImportError(RuntimeError):
    """Raised when a migration bundle cannot be safely staged."""


FORMAT = "ch17-sqlite-unified-candidate-v1"
RECORDS_FORMAT = "ch17-sqlite-migration-records-v1"
ADMISSION_PREFIX = b"/cnc/admission/unified/v2/"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateImportError(f"cannot read JSON input {path}: {exc}") from exc


def _required_int(value: Any, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise CandidateImportError(f"{name} must be an integer >= {minimum}")
    return value


def _verify_records(manifest: dict[str, Any], records: dict[str, Any]) -> None:
    if manifest.get("format") != "ch17-sqlite-migration-inventory-v1":
        raise CandidateImportError("unsupported inventory manifest format")
    if manifest.get("integrity", {}).get("status") != "PASS":
        raise CandidateImportError("source inventory integrity status is not PASS")
    if manifest.get("source", {}).get("changed_during_scan") is not False:
        raise CandidateImportError("source changed during inventory; repeat under a write freeze")
    if records.get("format") != RECORDS_FORMAT:
        raise CandidateImportError("unsupported migration records format")
    digest = manifest.get("snapshot_digest_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise CandidateImportError("manifest snapshot digest is missing or malformed")
    if records.get("snapshot_digest_sha256") != digest:
        raise CandidateImportError("manifest and records snapshot digests differ")

    tables = records.get("tables")
    summaries = manifest.get("table_summaries")
    if not isinstance(tables, dict) or not isinstance(summaries, dict):
        raise CandidateImportError("manifest summaries or records tables are malformed")
    if set(tables) != set(ALL_TABLES) or set(summaries) != set(ALL_TABLES):
        raise CandidateImportError("source table set does not match the supported legacy schema")

    for table, required_columns in ALL_TABLES.items():
        rows = tables[table]
        summary = summaries[table]
        if not isinstance(rows, list) or not isinstance(summary, dict):
            raise CandidateImportError(f"{table} records or summary are malformed")
        hasher = hashlib.sha256()
        for row in rows:
            if not isinstance(row, dict) or not required_columns.issubset(row):
                raise CandidateImportError(f"{table} contains a malformed row")
            hasher.update(_json_bytes(row))
            hasher.update(b"\n")
        if len(rows) != summary.get("row_count"):
            raise CandidateImportError(f"{table} row count does not match inventory")
        if hasher.hexdigest() != summary.get("records_sha256"):
            raise CandidateImportError(f"{table} record digest does not match inventory")

    admission_meta_from_records = {
        row["key"]: row["value"] for row in tables["coordinator_meta"]
    }
    authority_meta_from_records = {
        row["key"]: row["value"] for row in tables["coordinator_authority_meta"]
    }
    if admission_meta_from_records != manifest.get("admission_meta"):
        raise CandidateImportError("Admission metadata differs between manifest and records")
    if authority_meta_from_records != manifest.get("coordinator_authority_meta"):
        raise CandidateImportError("Coordinator metadata differs between manifest and records")
    leader_rows = tables["coordinator_authority_leader"]
    if len(leader_rows) != 1 or leader_rows[0] != manifest.get("derived", {}).get("leader"):
        raise CandidateImportError("Leader record differs between manifest and records")

    material = {
        "schema": manifest.get("schema"),
        "table_summaries": summaries,
        "admission_meta": manifest.get("admission_meta"),
        "authority_meta": manifest.get("coordinator_authority_meta"),
        "leader": manifest.get("derived", {}).get("leader"),
    }
    if _sha256(_json_bytes(material)) != digest:
        raise CandidateImportError("manifest snapshot digest does not verify")


def _policy(policy: Any, expected_hash: str) -> dict[str, Any]:
    required = {"global_limits", "tenant_limits", "max_waiters", "aging_interval_seconds"}
    if not isinstance(policy, dict) or set(policy) != required:
        raise CandidateImportError("policy JSON must contain exactly " + ", ".join(sorted(required)))
    global_limits = policy["global_limits"]
    tenant_limits = policy["tenant_limits"]
    max_waiters = _required_int(policy["max_waiters"], "max_waiters")
    aging = policy["aging_interval_seconds"]
    domains = {"read", "write", "multipart", "inventory"}
    if not isinstance(global_limits, dict) or set(global_limits) != domains:
        raise CandidateImportError("global_limits must define read/write/multipart/inventory")
    for domain, value in global_limits.items():
        _required_int(value, f"global_limits.{domain}", 1)
    if not isinstance(tenant_limits, dict):
        raise CandidateImportError("tenant_limits must be an object")
    for tenant, limits in tenant_limits.items():
        if not isinstance(tenant, str) or not tenant.strip() or not isinstance(limits, dict):
            raise CandidateImportError("tenant_limits contains an invalid tenant entry")
        if set(limits) - domains:
            raise CandidateImportError(f"tenant {tenant} has an unknown domain")
        for domain, value in limits.items():
            _required_int(value, f"tenant_limits.{tenant}.{domain}", 1)
    if (
        not isinstance(aging, (int, float)) or isinstance(aging, bool)
        or not math.isfinite(float(aging)) or float(aging) <= 0
    ):
        raise CandidateImportError("aging_interval_seconds must be finite and positive")
    normalized = {
        "global_limits": dict(sorted(global_limits.items())),
        "tenant_limits": {
            tenant: dict(sorted(limits.items()))
            for tenant, limits in sorted(tenant_limits.items())
        },
        "max_waiters": max_waiters,
        "aging_interval_seconds": float(aging),
    }
    actual = _sha256(json.dumps(
        normalized, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"))
    if actual != expected_hash:
        raise CandidateImportError("supplied policy does not match the legacy policy_hash")
    return normalized


def _request_key(request_id: str) -> str:
    digest = _sha256(request_id.encode("utf-8"))
    return "requests/" + digest


def build_candidate(
    manifest: dict[str, Any],
    records: dict[str, Any],
    policy_input: dict[str, Any],
    *,
    generated_at: float,
) -> dict[str, Any]:
    _verify_records(manifest, records)
    if not isinstance(generated_at, (int, float)) or isinstance(generated_at, bool):
        raise CandidateImportError("generated_at must be a finite timestamp")
    if not math.isfinite(float(generated_at)):
        raise CandidateImportError("generated_at must be a finite timestamp")

    admission_meta = manifest.get("admission_meta")
    authority_meta = manifest.get("coordinator_authority_meta")
    derived = manifest.get("derived", {})
    if not isinstance(admission_meta, dict) or not isinstance(authority_meta, dict):
        raise CandidateImportError("source metadata is malformed")
    if admission_meta.get("schema_version") != "1" or authority_meta.get("schema_version") != "1":
        raise CandidateImportError("unsupported legacy Admission/Coordinator schema version")
    policy = _policy(policy_input, admission_meta.get("policy_hash", ""))

    tables = records["tables"]
    active = [r for r in tables["admission_requests"] if r.get("state") == "ACTIVE"]
    waiters = tables["admission_waiters"]
    pending_states = {"PENDING_ACTIVATION", "REVOKING", "PENDING_PUBLISH", "RECOVERY_REVIEW"}
    pending = [r for r in tables["coordinator_authority_operations"] if r.get("state") in pending_states]
    if active or waiters or pending:
        raise CandidateImportError(
            "source is not quiescent: active leases={}, waiters={}, pending operations={}; "
            "drain and re-inventory before candidate import".format(len(active), len(waiters), len(pending))
        )
    if derived.get("active_but_expired_admission_rows", 0):
        raise CandidateImportError("expired-but-ACTIVE source rows require explicit source cleanup and re-inventory")

    leader_rows = tables["coordinator_authority_leader"]
    if len(leader_rows) != 1 or leader_rows[0].get("singleton") != 1:
        raise CandidateImportError("source must contain exactly one singleton Leader row")
    leader = leader_rows[0]
    leader_epoch = _required_int(leader.get("epoch"), "leader epoch")
    if leader.get("state") not in {"ACTIVE", "EXPIRED", "RELEASED", "NONE", "UNCLAIMED", "FENCED"}:
        raise CandidateImportError("source Leader state is unknown")

    scopes: dict[str, Any] = {}
    for row in tables["coordinator_authority_scopes"]:
        scope = row["scope"]
        if scope in scopes:
            raise CandidateImportError(f"duplicate Coordinator scope: {scope}")
        high_water = _required_int(row["high_water_token"], f"{scope}.high_water_token")
        sequence = _required_int(row["latest_operation_sequence"], f"{scope}.latest_operation_sequence")
        scopes[scope] = {
            "high_water_token": high_water,
            "lease_id": None,
            "owner_id": None,
            "tenant_id": None,
            "domain": None,
            "lease_expires_at": None,
            "lease_state": ("IDLE" if row["lease_state"] in {"IDLE", "REVOKED"} else "RECOVERY_REQUIRED"),
            "latest_operation_sequence": sequence,
            "provider_generation": row["provider_generation"],
            "updated_at": float(row["updated_at"]),
        }

    operations: dict[str, Any] = {}
    for row in tables["coordinator_authority_operations"]:
        scope = row["scope"]
        idem = row["idempotency_key"]
        if scope not in scopes:
            raise CandidateImportError(f"operation references missing scope: {scope}")
        key = _sha256((scope + "\x00" + idem).encode("utf-8"))
        if key in operations:
            raise CandidateImportError("duplicate Coordinator operation idempotency key")
        operations[key] = {
            "scope": scope,
            "kind": row["kind"],
            "idempotency_key": idem,
            "request_sha256": row["request_sha256"],
            "fencing_token": _required_int(row["fencing_token"], "operation fencing_token"),
            "operation_sequence": (
                None if row["operation_sequence"] is None
                else _required_int(row["operation_sequence"], "operation sequence")
            ),
            "lease_id": row["lease_id"],
            "owner_id": row["owner_id"],
            "tenant_id": row["tenant_id"],
            "domain": row["domain"],
            "lease_expires_at": float(row["lease_expires_at"]),
            "state": row["state"],
            "provider_generation": row["provider_generation"],
            "manifest_key": row["manifest_key"],
            "manifest_sha256": row["manifest_sha256"],
            "created_at": float(row["created_at"]),
            "updated_at": float(row["updated_at"]),
        }

    admission_floor = _required_int(admission_meta.get("next_fencing_token"), "Admission fencing floor")
    request_max = max(
        (_required_int(r["fencing_token"], "request fencing token") for r in tables["admission_requests"]),
        default=0,
    )
    if admission_floor < request_max:
        raise CandidateImportError("Admission fencing floor is below request history")
    if any(
        scopes[row["scope"]]["high_water_token"] < row["fencing_token"]
        or (
            row["operation_sequence"] is not None
            and scopes[row["scope"]]["latest_operation_sequence"] < row["operation_sequence"]
        )
        for row in tables["coordinator_authority_operations"]
    ):
        raise CandidateImportError("Coordinator scope high-water is below operation history")

    state = {
        "schema_version": 2,
        "policy_hash": admission_meta["policy_hash"],
        "global_limits": policy["global_limits"],
        "tenant_limits": policy["tenant_limits"],
        "max_waiters": policy["max_waiters"],
        "aging_interval_seconds": policy["aging_interval_seconds"],
        "next_fencing_token": admission_floor,
        "next_waiter_sequence": 0,
        "active": {},
        "waiters": [],
        "coordinator": {"leader": None, "scopes": scopes, "operations": operations},
        "counters": {
            "issued_leases": _required_int(admission_meta.get("issued_leases"), "issued_leases"),
            "expired_leases": _required_int(admission_meta.get("expired_leases"), "expired_leases"),
            "released_leases": sum(1 for r in tables["admission_requests"] if r["state"] == "RELEASED"),
            "rejected_capacity": _required_int(admission_meta.get("rejected_capacity"), "rejected_capacity"),
            "rejected_queue": _required_int(admission_meta.get("rejected_queue"), "rejected_queue"),
        },
    }
    request_indexes = []
    seen_request_ids = set()
    for row in tables["admission_requests"]:
        request_id = row["request_id"]
        if request_id in seen_request_ids:
            raise CandidateImportError(f"duplicate admission request ID: {request_id}")
        seen_request_ids.add(request_id)
        if row["state"] not in {"RELEASED", "EXPIRED"}:
            raise CandidateImportError(f"unsupported terminal request state: {row['state']}")
        record = {
            "request_id": request_id,
            "lease_id": row["lease_id"],
            "owner_id": row["owner_id"],
            "task_id": row["task_id"],
            "tenant_id": row["tenant_id"],
            "domain": row["domain"],
            "fencing_token": _required_int(row["fencing_token"], "request fencing token"),
            "expires_at": float(row["expires_at"]),
            "state": row["state"],
            "backend_lease_id": 1,  # terminal-only sentinel; never attached to a native lease
        }
        request_indexes.append({"key": _request_key(request_id), "record": record})

    leader_epoch_floor = leader_epoch
    external_fencing_reconciliation = "REQUIRED"
    candidate = {
        "format": FORMAT,
        "source_snapshot_digest_sha256": manifest["snapshot_digest_sha256"],
        "generated_at_unix": float(generated_at),
        "target": {
            "namespace": None,
            "namespace_must_be_explicit": True,
            "mode": "ISOLATED_CANDIDATE_ONLY",
            "requires_empty_namespace": True,
            "production_write_allowed": False,
        },
        "state_template": state,
        "terminal_request_indexes": request_indexes,
        "recovery_requirements": {
            "leader_epoch_floor": leader_epoch_floor,
            "leader_must_be_reclaimed": True,
            "external_fencing_reconciliation": external_fencing_reconciliation,
            "external_fencing_floor": None,
            "provider_operations_must_be_reconciled_before_activation": True,
            "active_lease_ttl_keys_are_not_imported": True,
            "terminal_request_backend_lease_id_sentinel": 1,
            "terminal_request_backend_lease_id_is_not_a_live_lease": True,
        },
        "legacy_metadata": {
            "attestations_issued": _required_int(admission_meta.get("attestations_issued"), "attestations_issued"),
            "coordinator_schema_version": authority_meta["schema_version"],\n        },\n        "counts": {
            "terminal_requests": len(request_indexes),
            "scopes": len(scopes),
            "operations": len(operations),
            "active_leases": 0,
            "waiters": 0,
            "pending_operations": 0,
        },
    }
    candidate["candidate_digest_sha256"] = _sha256(_json_bytes(candidate))
    return candidate


def _write_private_json(path: Path, payload: Any) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a verified isolated Unified schema-v2 candidate import bundle")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path, help="JSON policy matching legacy policy_hash")
    parser.add_argument("--output", required=True, type=Path, help="private candidate bundle output")
    args = parser.parse_args(argv)
    inputs = [p.expanduser().resolve() for p in (args.manifest, args.records, args.policy)]
    output = args.output.expanduser().resolve()
    if output in inputs or len(set(inputs)) != len(inputs):
        parser.error("input and output paths must be distinct")
    try:
        result = build_candidate(
            _read_json(inputs[0]), _read_json(inputs[1]), _read_json(inputs[2]),
            generated_at=time.time(),
        )
        _write_private_json(output, result)
    except (CandidateImportError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "CANDIDATE_BUNDLE_READY",
        "candidate_digest_sha256": result["candidate_digest_sha256"],
        "output": str(output),
        "counts": result["counts"],
        "recovery_requirements": result["recovery_requirements"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

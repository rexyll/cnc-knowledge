#!/usr/bin/env python3
"""Read-only inventory/export for legacy CH17 SQLite Coordinator databases.

This tool never instantiates the legacy Coordinator classes: their constructors
create/upgrade tables and may change journal mode. The inventory connection uses
SQLite URI mode=ro plus query_only and a single read transaction.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

ADMISSION_TABLES = {
    "coordinator_meta": {"key", "value"},
    "admission_requests": {
        "request_id", "lease_id", "owner_id", "task_id", "tenant_id",
        "domain", "fencing_token", "expires_at", "state",
    },
    "admission_waiters": {
        "sequence", "request_id", "owner_id", "task_id", "tenant_id",
        "domain", "priority", "queued_at", "expires_at",
    },
}
AUTHORITY_TABLES = {
    "coordinator_authority_meta": {"key", "value"},
    "coordinator_authority_leader": {
        "singleton", "leader_id", "epoch", "expires_at", "state",
    },
    "coordinator_authority_scopes": {
        "scope", "high_water_token", "lease_id", "owner_id", "tenant_id",
        "domain", "lease_expires_at", "lease_state",
        "latest_operation_sequence", "provider_generation", "updated_at",
    },
    "coordinator_authority_operations": {
        "scope", "idempotency_key", "kind", "request_sha256", "fencing_token",
        "operation_sequence", "lease_id", "owner_id", "tenant_id", "domain",
        "lease_expires_at", "manifest_key", "manifest_sha256", "state",
        "provider_generation", "created_at", "updated_at",
    },
}
ALL_TABLES = {**ADMISSION_TABLES, **AUTHORITY_TABLES}


class InventoryError(RuntimeError):
    """Raised when a source database cannot be safely inventoried."""


def _canonical(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"$bytes_base64": base64.b64encode(value).decode("ascii")}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise InventoryError(f"unsupported SQLite value type: {type(value).__name__}")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "sha256": digest.hexdigest(),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _source_fingerprints(path: Path) -> dict[str, Any]:
    # The -shm file is transient and may be touched by a read-only WAL connection.
    # Compare only durable database/WAL content for concurrent-writer detection.
    return {
        suffix or "database": _sha256_file(Path(str(path) + suffix) if suffix else path)
        for suffix in ("", "-wal")
    }


def _open_read_only(path: Path) -> sqlite3.Connection:
    # as_uri() escapes spaces, '#', '?' and other URI-significant path bytes.
    uri = path.as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5.0, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row["name"])
        for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    }


def _primary_key_order(connection: sqlite3.Connection, table: str) -> list[str]:
    rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [
        str(row["name"])
        for row in sorted(rows, key=lambda item: int(item["pk"]) if item["pk"] else 9999)
        if int(row["pk"]) > 0
    ]


def _read_table(
    connection: sqlite3.Connection, table: str, *, include_records: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
    primary_key = _primary_key_order(connection, table)
    if not primary_key:
        raise InventoryError(f"table {table} has no declared primary key")
    order_by = ",".join('"' + column.replace('"', '""') + '"' for column in primary_key)
    cursor = connection.execute(f'SELECT * FROM "{table}" ORDER BY {order_by}')
    digest = hashlib.sha256()
    count = 0
    records: list[dict[str, Any]] | None = [] if include_records else None
    state_counts: dict[str, int] = {}
    min_values: dict[str, Any] = {}
    max_values: dict[str, Any] = {}
    for raw in cursor:
        record = {key: _canonical(raw[key]) for key in raw.keys()}
        encoded = _json_bytes(record)
        digest.update(encoded)
        digest.update(b"\n")
        count += 1
        if "state" in record and isinstance(record["state"], str):
            state_counts[record["state"]] = state_counts.get(record["state"], 0) + 1
        for column in ("sequence", "fencing_token", "high_water_token",
                       "latest_operation_sequence", "epoch", "expires_at"):
            value = record.get(column)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                min_values[column] = value if column not in min_values else min(min_values[column], value)
                max_values[column] = value if column not in max_values else max(max_values[column], value)
        if records is not None:
            records.append(record)
    summary: dict[str, Any] = {
        "row_count": count,
        "primary_key": primary_key,
        "records_sha256": digest.hexdigest(),
    }
    if state_counts:
        summary["state_counts"] = dict(sorted(state_counts.items()))
    if min_values:
        summary["numeric_min"] = min_values
        summary["numeric_max"] = max_values
    return summary, records


def build_inventory(
    database_path: str | os.PathLike[str],
    *,
    captured_at: float | None = None,
    include_records: bool = False,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]] | None]:
    path = Path(database_path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise InventoryError("source path must be a regular SQLite database file")
    if path.stat().st_size == 0:
        raise InventoryError("source database is empty")
    started = time.time()
    before = _source_fingerprints(path)
    connection: sqlite3.Connection | None = None
    try:
        connection = _open_read_only(path)
        connection.execute("BEGIN")
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        integrity_rows = [str(row[0]) for row in connection.execute("PRAGMA integrity_check").fetchall()]
        integrity_ok = integrity_rows == ["ok"]
        foreign_key_errors = [
            dict(row)
            for row in connection.execute("PRAGMA foreign_key_check").fetchall()
        ]
        existing = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        missing = sorted(set(ALL_TABLES) - existing)
        if missing:
            raise InventoryError(
                "database is missing required Admission/Coordinator tables: " + ", ".join(missing)
            )

        schema: dict[str, Any] = {}
        errors: list[str] = []
        warnings: list[str] = []
        for table, required_columns in ALL_TABLES.items():
            actual = _table_columns(connection, table)
            missing_columns = sorted(required_columns - actual)
            extra_columns = sorted(actual - required_columns)
            schema[table] = {
                "required_columns": sorted(required_columns),
                "actual_columns": sorted(actual),
                "missing_columns": missing_columns,
                "extra_columns": extra_columns,
            }
            if missing_columns:
                errors.append(f"{table} missing columns: {', '.join(missing_columns)}")
            if extra_columns:
                warnings.append(f"{table} has unrecognized columns: {', '.join(extra_columns)}")

        if errors:
            raise InventoryError("; ".join(errors))

        table_summaries: dict[str, Any] = {}
        exported: dict[str, list[dict[str, Any]]] | None = (
            {} if include_records else None
        )
        for table in ALL_TABLES:
            summary, records = _read_table(
                connection, table, include_records=include_records,
            )
            table_summaries[table] = summary
            if exported is not None:
                exported[table] = records or []

        admission_meta = {
            str(row["key"]): str(row["value"])
            for row in connection.execute("SELECT key,value FROM coordinator_meta ORDER BY key")
        }
        authority_meta = {
            str(row["key"]): str(row["value"])
            for row in connection.execute(
                "SELECT key,value FROM coordinator_authority_meta ORDER BY key"
            )
        }
        required_admission_meta = {
            "schema_version", "policy_hash", "next_fencing_token", "issued_leases",
            "expired_leases", "rejected_capacity", "rejected_queue", "attestations_issued",
        }
        missing_admission_meta = sorted(required_admission_meta - set(admission_meta))
        if missing_admission_meta:
            errors.append("Admission metadata keys missing: " + ", ".join(missing_admission_meta))
        if "schema_version" not in authority_meta:
            errors.append("Coordinator authority schema_version metadata is missing")
        if admission_meta.get("schema_version") != "1":
            errors.append("unsupported Admission schema_version (expected 1)")
        if authority_meta.get("schema_version") != "1":
            errors.append("unsupported Coordinator authority schema_version (expected 1)")
        for key, value in admission_meta.items():
            if key in {"next_fencing_token", "issued_leases", "expired_leases",
                       "rejected_capacity", "rejected_queue", "attestations_issued"}:
                try:
                    if int(value) < 0:
                        raise ValueError
                except ValueError:
                    errors.append(f"Admission metadata {key} is not a non-negative integer")

        if captured_at is not None and (
            not isinstance(captured_at, (int, float)) or isinstance(captured_at, bool)
        ):
            raise InventoryError("captured_at must be a finite numeric timestamp")
        now = time.time() if captured_at is None else float(captured_at)
        if not (now == now and abs(now) != float("inf")):
            raise InventoryError("captured_at must be a finite timestamp")

        active_rows = connection.execute(
            "SELECT COUNT(*) AS n FROM admission_requests "
            "WHERE state='ACTIVE' AND expires_at>?", (now,),
        ).fetchone()
        expired_active_rows = connection.execute(
            "SELECT COUNT(*) AS n FROM admission_requests "
            "WHERE state='ACTIVE' AND expires_at<=?", (now,),
        ).fetchone()
        expired_waiters = connection.execute(
            "SELECT COUNT(*) AS n FROM admission_waiters WHERE expires_at<=?", (now,),
        ).fetchone()
        leader_rows = connection.execute(
            "SELECT * FROM coordinator_authority_leader ORDER BY singleton"
        ).fetchall()
        if len(leader_rows) != 1 or int(leader_rows[0]["singleton"]) != 1:
            errors.append("Coordinator authority must contain exactly one singleton Leader row")

        admission_floor = int(admission_meta.get("next_fencing_token", "0") or "0")
        max_request_token = int(connection.execute(
            "SELECT COALESCE(MAX(fencing_token),0) FROM admission_requests"
        ).fetchone()[0])
        if admission_floor < max_request_token:
            errors.append("Admission next_fencing_token is below admission_requests fencing_token maximum")

        duplicate_waiter_requests = int(connection.execute(
            "SELECT COUNT(*) FROM admission_waiters w "
            "JOIN admission_requests r ON r.request_id=w.request_id"
        ).fetchone()[0])
        if duplicate_waiter_requests:
            errors.append("request_id appears in both admission_waiters and admission_requests")

        scopes = connection.execute(
            "SELECT scope,high_water_token,latest_operation_sequence "
            "FROM coordinator_authority_scopes ORDER BY scope"
        ).fetchall()
        scope_violations = []
        for scope in scopes:
            operation = connection.execute(
                "SELECT COALESCE(MAX(fencing_token),0),"
                "COALESCE(MAX(operation_sequence),0) "
                "FROM coordinator_authority_operations WHERE scope=?",
                (scope["scope"],),
            ).fetchone()
            if int(scope["high_water_token"]) < int(operation[0]):
                scope_violations.append({
                    "scope": str(scope["scope"]), "kind": "fencing_token",
                    "scope_floor": int(scope["high_water_token"]), "operation_max": int(operation[0]),
                })
            if int(scope["latest_operation_sequence"]) < int(operation[1]):
                scope_violations.append({
                    "scope": str(scope["scope"]), "kind": "operation_sequence",
                    "scope_floor": int(scope["latest_operation_sequence"]),
                    "operation_max": int(operation[1]),
                })
        if scope_violations:
            errors.append("one or more Coordinator scope high-water marks are below operation history")

        orphan_operations = int(connection.execute(
            "SELECT COUNT(*) FROM coordinator_authority_operations o "
            "LEFT JOIN coordinator_authority_scopes s ON s.scope=o.scope "
            "WHERE s.scope IS NULL"
        ).fetchone()[0])
        if orphan_operations:
            errors.append("Coordinator operation rows reference missing scopes")

        if journal_mode != "wal":
            warnings.append(f"source journal_mode is {journal_mode!r}; expected WAL for the legacy same-host backend")
        if not integrity_ok:
            errors.append("SQLite integrity_check did not return exactly 'ok'")
        if foreign_key_errors:
            errors.append("SQLite foreign_key_check reported violations")
        pending_operations = int(connection.execute(
            "SELECT COUNT(*) FROM coordinator_authority_operations "
            "WHERE state IN ('PENDING_ACTIVATION','REVOKING','PENDING_PUBLISH','RECOVERY_REVIEW')"
        ).fetchone()[0])
        malformed_operation_digests = int(connection.execute(
            "SELECT COUNT(*) FROM coordinator_authority_operations "
            "WHERE length(request_sha256) != 64 OR request_sha256 GLOB '*[^0-9a-f]*' "
            "OR (manifest_sha256 IS NOT NULL AND "
            "(length(manifest_sha256) != 64 OR manifest_sha256 GLOB '*[^0-9a-f]*'))"
        ).fetchone()[0])
        if malformed_operation_digests:
            errors.append("Coordinator operation rows contain malformed SHA-256 fields")
        leader = dict(leader_rows[0]) if len(leader_rows) == 1 else None
        snapshot_material = {
            "schema": schema,
            "table_summaries": table_summaries,
            "admission_meta": admission_meta,
            "authority_meta": authority_meta,
            "leader": leader,
        }
        snapshot_digest = hashlib.sha256(_json_bytes(snapshot_material)).hexdigest()
        connection.commit()
        after = _source_fingerprints(path)
        source_changed = before != after
        if source_changed:
            warnings.append("source database or SQLite sidecar files changed during inventory; repeat under a write freeze")
        finished = time.time()
        report = {
            "format": "ch17-sqlite-migration-inventory-v1",
            "source": {
                "database_path": str(path),
                "file_fingerprints_before": before,
                "file_fingerprints_after": after,
                "changed_during_scan": source_changed,
            },
            "captured_at_unix": now,
            "scan_duration_seconds": round(finished - started, 6),
            "sqlite": {
                "version": sqlite3.sqlite_version,
                "journal_mode": journal_mode,
                "read_only_uri": True,
                "query_only": True,
                "integrity_check": integrity_rows,
                "foreign_key_violation_count": len(foreign_key_errors),
            },
            "schema": schema,
            "table_summaries": table_summaries,
            "admission_meta": admission_meta,
            "coordinator_authority_meta": authority_meta,
            "derived": {
                "active_admission_leases_at_capture": int(active_rows["n"]),
                "active_but_expired_admission_rows": int(expired_active_rows["n"]),
                "expired_waiters_at_capture": int(expired_waiters["n"]),
                "admission_next_fencing_token": admission_floor,
                "admission_request_max_fencing_token": max_request_token,
                "coordinator_scope_count": len(scopes),
                "coordinator_operation_orphan_count": orphan_operations,
                "coordinator_malformed_digest_count": malformed_operation_digests,
                "scope_high_water_violations": scope_violations,
                "pending_operation_count": pending_operations,
                "leader": leader,
            },
            "integrity": {
                "errors": errors,
                "warnings": warnings,
                "status": "PASS" if not errors else "FAIL",
            },
            "snapshot_digest_sha256": snapshot_digest,
        }
        return report, exported
    except sqlite3.Error as exc:
        if connection is not None:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
        raise InventoryError(f"read-only SQLite inventory failed: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()


def _write_private_json(path: Path, payload: Any) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    import tempfile

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only inventory/export of legacy CH17 SQLite Admission and Coordinator state"
    )
    parser.add_argument("--database", required=True, type=Path, help="existing SQLite database file")
    parser.add_argument("--output", required=True, type=Path, help="inventory manifest JSON path")
    parser.add_argument(
        "--records-output", type=Path,
        help="optional private JSON export containing every source row (contains operational identifiers)",
    )
    args = parser.parse_args(argv)
    source = args.database.expanduser().resolve()
    outputs = [args.output.expanduser().resolve()]
    if args.records_output is not None:
        outputs.append(args.records_output.expanduser().resolve())
    if source in outputs or len(set(outputs)) != len(outputs):
        parser.error("source database and output paths must be distinct")
    try:
        report, records = build_inventory(source, include_records=args.records_output is not None)
        _write_private_json(args.output, report)
        if args.records_output is not None:
            _write_private_json(args.records_output, {
                "format": "ch17-sqlite-migration-records-v1",
                "snapshot_digest_sha256": report["snapshot_digest_sha256"],
                "tables": records,
            })
    except (InventoryError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": report["integrity"]["status"],
        "snapshot_digest_sha256": report["snapshot_digest_sha256"],
        "inventory_output": str(args.output),
        "records_output": None if args.records_output is None else str(args.records_output),
        "errors": report["integrity"]["errors"],
        "warnings": report["integrity"]["warnings"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["integrity"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

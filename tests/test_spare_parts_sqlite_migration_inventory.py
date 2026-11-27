from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.spare_parts_provider_admission_sqlite import SQLiteProviderAdmissionCoordinator
from scripts.spare_parts_provider_coordinator_authority import SQLiteDurableCoordinatorAuthority
from scripts.spare_parts_sqlite_migration_inventory import (
    InventoryError, _open_read_only, build_inventory,
)


class SQLiteMigrationInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tmp.name) / "legacy.sqlite3"
        SQLiteProviderAdmissionCoordinator(
            self.database_path,
            global_limits={"read": 2, "write": 2, "multipart": 1, "inventory": 1},
            max_waiters=8,
        )
        SQLiteDurableCoordinatorAuthority(self.database_path)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "INSERT INTO admission_requests VALUES(?,?,?,?,?,?,?,?,?)",
                ("request-active", "lease-active", "owner-A", "task-A", "tenant-A",
                 "read", 7, 2000.0, "ACTIVE"),
            )
            connection.execute(
                "INSERT INTO admission_waiters"
                "(sequence,request_id,owner_id,task_id,tenant_id,domain,priority,queued_at,expires_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (4, "request-waiting", "owner-B", "task-B", "tenant-A",
                 "read", 2, 900.0, 2100.0),
            )
            connection.execute(
                "UPDATE coordinator_meta SET value='7' WHERE key='next_fencing_token'"
            )
            connection.execute(
                "INSERT INTO coordinator_authority_scopes"
                "(scope,high_water_token,lease_id,owner_id,tenant_id,domain,lease_expires_at,"
                "lease_state,latest_operation_sequence,provider_generation,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("tenants/tenant-A/cnc/ch17/spares/pkg-001", 9, "lease-active",
                 "owner-A", "tenant-A", "read", 2000.0, "ACTIVE", 3, "provider-gen-1", 950.0),
            )
            connection.execute(
                "INSERT INTO coordinator_authority_operations"
                "(scope,idempotency_key,kind,request_sha256,fencing_token,operation_sequence,"
                "lease_id,owner_id,tenant_id,domain,lease_expires_at,manifest_key,manifest_sha256,"
                "state,provider_generation,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("tenants/tenant-A/cnc/ch17/spares/pkg-001", "publish-1", "PUBLISH",
                 "a" * 64, 9, 3, "lease-active", "owner-A", "tenant-A", "read",
                 2000.0, "manifest/key", "b" * 64, "COMMITTED", "provider-gen-1", 951.0, 952.0),
            )

    def tearDown(self):
        self.tmp.cleanup()

    def test_inventory_reports_schema_counts_floors_and_deterministic_table_hashes(self):
        report, records = build_inventory(
            self.database_path, captured_at=1000.0, include_records=True,
        )
        self.assertEqual(report["integrity"]["status"], "PASS")
        self.assertEqual(report["sqlite"]["read_only_uri"], True)
        self.assertEqual(report["derived"]["active_admission_leases_at_capture"], 1)
        self.assertEqual(report["derived"]["expired_waiters_at_capture"], 0)
        self.assertEqual(report["derived"]["admission_next_fencing_token"], 7)
        self.assertEqual(report["derived"]["coordinator_scope_count"], 1)
        self.assertEqual(report["derived"]["pending_operation_count"], 0)
        self.assertEqual(
            report["table_summaries"]["admission_requests"]["row_count"], 1,
        )
        self.assertEqual(len(records["coordinator_authority_operations"]), 1)
        self.assertEqual(
            report["table_summaries"]["admission_requests"]["records_sha256"],
            hashlib.sha256(
                (json.dumps({
                    "request_id": "request-active", "lease_id": "lease-active",
                    "owner_id": "owner-A", "task_id": "task-A", "tenant_id": "tenant-A",
                    "domain": "read", "fencing_token": 7, "expires_at": 2000.0,
                    "state": "ACTIVE",
                }, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
            ).hexdigest(),
        )

    def test_inventory_does_not_modify_source_database(self):
        before = hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        build_inventory(self.database_path, captured_at=1000.0)
        after = hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_read_only_connection_rejects_mutations(self):
        connection = _open_read_only(self.database_path)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute(
                    "UPDATE coordinator_meta SET value='999' WHERE key='next_fencing_token'"
                )
        finally:
            connection.close()

    def test_inventory_flags_fencing_and_sequence_floor_regressions(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE coordinator_meta SET value='6' WHERE key='next_fencing_token'"
            )
            connection.execute(
                "UPDATE coordinator_authority_scopes "
                "SET high_water_token=8,latest_operation_sequence=2"
            )
        report, _ = build_inventory(self.database_path, captured_at=1000.0)
        self.assertEqual(report["integrity"]["status"], "FAIL")
        self.assertGreaterEqual(len(report["integrity"]["errors"]), 2)

    def test_inventory_rejects_database_missing_required_tables(self):
        incomplete = Path(self.tmp.name) / "incomplete.sqlite3"
        with sqlite3.connect(incomplete) as connection:
            connection.execute("CREATE TABLE unrelated(value TEXT)")
        with self.assertRaises(InventoryError):
            build_inventory(incomplete)

    def test_inventory_does_not_run_expiry_cleanup(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE admission_requests SET expires_at=1.0 WHERE request_id='request-active'"
            )
        before = hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        report, _ = build_inventory(self.database_path, captured_at=1000.0)
        after = hashlib.sha256(self.database_path.read_bytes()).hexdigest()
        self.assertEqual(report["derived"]["active_but_expired_admission_rows"], 1)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

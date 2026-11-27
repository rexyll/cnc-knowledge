from __future__ import annotations

import copy
import hashlib
import json
import unittest

from scripts.spare_parts_sqlite_candidate_importer import (
    CandidateImportError, build_candidate,
)
from scripts.spare_parts_sqlite_migration_inventory import ALL_TABLES, _json_bytes


def policy_fixture():
    return {
        "global_limits": {"read": 4, "write": 2, "multipart": 2, "inventory": 1},
        "tenant_limits": {"tenant-A": {"read": 2}},
        "max_waiters": 16,
        "aging_interval_seconds": 1.0,
    }


def _policy_hash(policy):
    normalized = {
        "global_limits": dict(sorted(policy["global_limits"].items())),
        "tenant_limits": {
            tenant: dict(sorted(limits.items()))
            for tenant, limits in sorted(policy["tenant_limits"].items())
        },
        "max_waiters": policy["max_waiters"],
        "aging_interval_seconds": float(policy["aging_interval_seconds"]),
    }
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def fixture():
    policy = policy_fixture()
    tables = {name: [] for name in ALL_TABLES}
    tables["coordinator_meta"] = [
        {"key": "schema_version", "value": "1"},
        {"key": "policy_hash", "value": _policy_hash(policy)},
        {"key": "next_fencing_token", "value": "7"},
        {"key": "issued_leases", "value": "5"},
        {"key": "expired_leases", "value": "1"},
        {"key": "rejected_capacity", "value": "2"},
        {"key": "rejected_queue", "value": "3"},
        {"key": "attestations_issued", "value": "0"},
    ]
    tables["coordinator_authority_meta"] = [{"key": "schema_version", "value": "1"}]
    tables["coordinator_authority_leader"] = [{
        "singleton": 1, "leader_id": "old-leader", "epoch": 8,
        "expires_at": 100.0, "state": "EXPIRED",
    }]
    scope = "tenants/tenant-A/cnc/ch17/spares/pkg-001"
    tables["coordinator_authority_scopes"] = [{
        "scope": scope, "high_water_token": 9, "lease_id": None,
        "owner_id": None, "tenant_id": None, "domain": None,
        "lease_expires_at": None, "lease_state": "IDLE",
        "latest_operation_sequence": 3, "provider_generation": "provider-gen-1",
        "updated_at": 950.0,
    }]
    tables["coordinator_authority_operations"] = [{
        "scope": scope, "idempotency_key": "publish-1", "kind": "PUBLISH",
        "request_sha256": "a" * 64, "fencing_token": 9, "operation_sequence": 3,
        "lease_id": "old-lease", "owner_id": "owner-A", "tenant_id": "tenant-A",
        "domain": "read", "lease_expires_at": 900.0, "manifest_key": "manifest/key",
        "manifest_sha256": "b" * 64, "state": "COMMITTED",
        "provider_generation": "provider-gen-1", "created_at": 951.0, "updated_at": 952.0,
    }]
    tables["admission_requests"] = [{
        "request_id": "request-1", "lease_id": "lease-1", "owner_id": "owner-A",
        "task_id": "task-A", "tenant_id": "tenant-A", "domain": "read",
        "fencing_token": 7, "expires_at": 900.0, "state": "RELEASED",
    }]
    summaries = {}
    for table, rows in tables.items():
        digest = hashlib.sha256()
        for row in rows:
            digest.update(_json_bytes(row))
            digest.update(b"\n")
        summaries[table] = {
            "row_count": len(rows),
            "primary_key": [],
            "records_sha256": digest.hexdigest(),
        }
    leader = tables["coordinator_authority_leader"][0]
    material = {
        "schema": {},
        "table_summaries": summaries,
        "admission_meta": {row["key"]: row["value"] for row in tables["coordinator_meta"]},
        "authority_meta": {"schema_version": "1"},
        "leader": leader,
    }
    snapshot = hashlib.sha256(_json_bytes(material)).hexdigest()
    manifest = {
        "format": "ch17-sqlite-migration-inventory-v1",
        "integrity": {"status": "PASS"},
        "source": {"changed_during_scan": False},
        "schema": {},
        "table_summaries": summaries,
        "admission_meta": material["admission_meta"],
        "coordinator_authority_meta": material["authority_meta"],
        "derived": {
            "active_but_expired_admission_rows": 0,
            "leader": leader,
        },
        "snapshot_digest_sha256": snapshot,
    }
    records = {
        "format": "ch17-sqlite-migration-records-v1",
        "snapshot_digest_sha256": snapshot,
        "tables": tables,
    }
    return manifest, records, policy


class CandidateImporterTests(unittest.TestCase):
    def test_builds_deterministic_quiescent_schema_v2_candidate(self):
        manifest, records, policy = fixture()
        result = build_candidate(manifest, records, policy, generated_at=1000.0)
        state = result["state_template"]
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["policy_hash"], manifest["admission_meta"]["policy_hash"])
        self.assertEqual(state["next_fencing_token"], 7)
        self.assertEqual(state["coordinator"]["scopes"][
            "tenants/tenant-A/cnc/ch17/spares/pkg-001"
        ]["high_water_token"], 9)
        self.assertIsNone(state["coordinator"]["leader"])
        self.assertEqual(result["recovery_requirements"]["leader_epoch_floor"], 8)
        self.assertIsNone(result["recovery_requirements"]["external_fencing_floor"])
        self.assertTrue(result["recovery_requirements"]["leader_must_be_reclaimed"])
        self.assertEqual(result["counts"]["terminal_requests"], 1)
        self.assertEqual(result["terminal_request_indexes"][0]["record"]["backend_lease_id"], 1)
        self.assertTrue(result["recovery_requirements"]["terminal_request_backend_lease_id_is_not_a_live_lease"])
        again = build_candidate(manifest, records, policy, generated_at=1000.0)
        self.assertEqual(result, again)

    def test_rejects_manifest_records_digest_mismatch(self):
        manifest, records, policy = fixture()
        records["tables"]["admission_requests"][0]["owner_id"] = "tampered"
        with self.assertRaises(CandidateImportError):
            build_candidate(manifest, records, policy, generated_at=1000.0)

    def test_rejects_policy_hash_mismatch(self):
        manifest, records, policy = fixture()
        policy["global_limits"]["read"] = 99
        with self.assertRaisesRegex(CandidateImportError, "policy"):
            build_candidate(manifest, records, policy, generated_at=1000.0)

    def test_rejects_active_leases_and_waiters(self):
        for table, row in (
            ("admission_requests", {
                "request_id": "active", "lease_id": "lease", "owner_id": "owner",
                "task_id": "task", "tenant_id": "tenant-A", "domain": "read",
                "fencing_token": 8, "expires_at": 2000.0, "state": "ACTIVE",
            }),
            ("admission_waiters", {
                "sequence": 1, "request_id": "waiting", "owner_id": "owner",
                "task_id": "task", "tenant_id": "tenant-A", "domain": "read",
                "priority": 1, "queued_at": 900.0, "expires_at": 2000.0,
            }),
        ):
            manifest, records, policy = fixture()
            records["tables"][table].append(row)
            with self.assertRaisesRegex(CandidateImportError, "not quiescent"):
                build_candidate(manifest, records, policy, generated_at=1000.0)

    def test_rejects_pending_operations_and_changed_source(self):
        manifest, records, policy = fixture()
        records["tables"]["coordinator_authority_operations"][0]["state"] = "PENDING_PUBLISH"
        with self.assertRaises(CandidateImportError):
            build_candidate(manifest, records, policy, generated_at=1000.0)
        manifest, records, policy = fixture()
        manifest["source"]["changed_during_scan"] = True
        with self.assertRaisesRegex(CandidateImportError, "changed"):
            build_candidate(manifest, records, policy, generated_at=1000.0)

    def test_non_idle_scope_is_quarantined_for_recovery(self):
        manifest, records, policy = fixture()
        records["tables"]["coordinator_authority_scopes"][0]["lease_state"] = "ACTIVE"
        # Recompute the source digest so this exercises semantic mapping, not corruption detection.
        for table, rows in records["tables"].items():
            digest = hashlib.sha256()
            for row in rows:
                digest.update(_json_bytes(row))
                digest.update(b"\n")
            manifest["table_summaries"][table]["records_sha256"] = digest.hexdigest()
        material = {
            "schema": manifest["schema"],
            "table_summaries": manifest["table_summaries"],
            "admission_meta": manifest["admission_meta"],
            "authority_meta": manifest["coordinator_authority_meta"],
            "leader": manifest["derived"]["leader"],
        }
        digest = hashlib.sha256(_json_bytes(material)).hexdigest()
        manifest["snapshot_digest_sha256"] = digest
        records["snapshot_digest_sha256"] = digest
        result = build_candidate(manifest, records, policy, generated_at=1000.0)
        scope = result["state_template"]["coordinator"]["scopes"][
            "tenants/tenant-A/cnc/ch17/spares/pkg-001"
        ]
        self.assertEqual(scope["lease_state"], "RECOVERY_REQUIRED")


if __name__ == "__main__":
    unittest.main()

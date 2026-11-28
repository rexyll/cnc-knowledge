from __future__ import annotations

import hashlib
import unittest

from scripts.spare_parts_sqlite_candidate_import_plan import (
    ImportPlanError,
    build_import_plan,
)
from scripts.spare_parts_sqlite_migration_inventory import _json_bytes


PREFIX = b"/cnc/migration/isolated/round77-plan/"


def candidate_fixture():
    request_id = "request-1"
    request = {
        "request_id": request_id,
        "lease_id": "legacy-lease-1",
        "owner_id": "owner-1",
        "task_id": "task-1",
        "tenant_id": "tenant-A",
        "domain": "read",
        "fencing_token": 7,
        "expires_at": 900.0,
        "state": "RELEASED",
        "backend_lease_id": 1,
    }
    state = {
        "schema_version": 2,
        "policy_hash": "a" * 64,
        "global_limits": {"read": 4, "write": 2, "multipart": 2, "inventory": 1},
        "tenant_limits": {"tenant-A": {"read": 2}},
        "max_waiters": 16,
        "aging_interval_seconds": 1.0,
        "next_fencing_token": 7,
        "next_waiter_sequence": 0,
        "active": {},
        "waiters": [],
        "coordinator": {
            "leader": {
                "leader_id": "migration-epoch-floor",
                "epoch": 8,
                "expires_at": 0.0,
                "backend_lease_id": 1,
            },
            "scopes": {
                "scope-1": {
                    "high_water_token": 9,
                    "lease_id": None,
                    "owner_id": None,
                    "tenant_id": None,
                    "domain": None,
                    "lease_expires_at": None,
                    "lease_state": "IDLE",
                    "latest_operation_sequence": 3,
                    "provider_generation": "generation-1",
                    "updated_at": 950.0,
                }
            },
            "operations": {},
        },
        "counters": {
            "issued_leases": 5,
            "expired_leases": 1,
            "released_leases": 1,
            "rejected_capacity": 2,
            "rejected_queue": 3,
        },
    }
    candidate = {
        "format": "ch17-sqlite-unified-candidate-v1",
        "source_snapshot_digest_sha256": "b" * 64,
        "generated_at_unix": 1000.0,
        "target": {
            "namespace": None,
            "namespace_must_be_explicit": True,
            "mode": "ISOLATED_CANDIDATE_ONLY",
            "requires_empty_namespace": True,
            "production_write_allowed": False,
        },
        "state_template": state,
        "terminal_request_indexes": [{
            "key": "requests/" + hashlib.sha256(request_id.encode()).hexdigest(),
            "record": request,
        }],
        "recovery_requirements": {
            "leader_epoch_floor": 8,
            "leader_epoch_floor_is_embedded_as_inactive_coordinator_record": True,
            "leader_epoch_floor_backend_lease_id_sentinel": 1,
            "leader_must_be_reclaimed": True,
            "external_fencing_reconciliation": "REQUIRED",
            "external_fencing_floor": None,
            "provider_operations_must_be_reconciled_before_activation": True,
            "active_lease_ttl_keys_are_not_imported": True,
            "terminal_request_backend_lease_id_sentinel": 1,
            "terminal_request_backend_lease_id_is_not_a_live_lease": True,
        },
        "legacy_metadata": {
            "attestations_issued": 0,
            "coordinator_schema_version": "1",
        },
        "counts": {
            "terminal_requests": 1,
            "scopes": 1,
            "operations": 0,
            "active_leases": 0,
            "waiters": 0,
            "pending_operations": 0,
        },
    }
    candidate["candidate_digest_sha256"] = hashlib.sha256(_json_bytes(candidate)).hexdigest()
    return candidate


def resign(candidate):
    material = dict(candidate)
    material.pop("candidate_digest_sha256", None)
    candidate["candidate_digest_sha256"] = hashlib.sha256(_json_bytes(material)).hexdigest()


class CandidateImportPlanTests(unittest.TestCase):
    def candidate(self):
        return candidate_fixture()

    def test_builds_atomic_single_transaction_plan(self):
        plan = build_import_plan(
            self.candidate(), PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000
        )
        self.assertTrue(plan["limits"]["fits"])
        self.assertEqual(plan["atomicity"]["transaction_count"], 1)
        self.assertEqual(plan["atomicity"]["compare_count"], 3)
        self.assertEqual(plan["atomicity"]["put_count"], 2)
        self.assertTrue(plan["atomicity"]["all_destination_keys_compared_as_version_zero"])
        self.assertTrue(plan["atomicity"]["state_and_terminal_indexes_commit_together"])
        self.assertEqual(plan["atomicity"]["native_lease_grants_required_for_import"], 0)
        self.assertFalse(plan["atomicity"]["legacy_leader_ttl_key_imported"])
        self.assertTrue(plan["target"]["leader_key_must_remain_absent_until_new_claim"])
        self.assertEqual(plan["payload_estimate"]["terminal_request_count"], 1)
        self.assertTrue(plan["not_performed"])

    def test_rejects_production_namespace(self):
        with self.assertRaises(ImportPlanError):
            build_import_plan(
                self.candidate(), b"/cnc/admission/unified/v2/",
                max_txn_ops=100, max_txn_bytes=1_000_000,
            )

    def test_rejects_modified_candidate_digest(self):
        candidate = self.candidate()
        candidate["state_template"]["next_fencing_token"] += 1
        with self.assertRaisesRegex(ImportPlanError, "digest"):
            build_import_plan(candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000)

    def test_rejects_request_index_key_mismatch(self):
        candidate = self.candidate()
        candidate["terminal_request_indexes"][0]["key"] = "requests/" + "0" * 64
        resign(candidate)
        with self.assertRaisesRegex(ImportPlanError, "key"):
            build_import_plan(candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000)

    def test_rejects_live_or_nonterminal_request_record(self):
        candidate = self.candidate()
        candidate["terminal_request_indexes"][0]["record"]["state"] = "ACTIVE"
        resign(candidate)
        with self.assertRaises(ImportPlanError):
            build_import_plan(candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000)

    def test_reports_operation_budget_exceeded_without_claiming_ready(self):
        plan = build_import_plan(
            self.candidate(), PREFIX, max_txn_ops=1, max_txn_bytes=1_000_000
        )
        self.assertFalse(plan["limits"]["fits"])
        self.assertIn("compare+put", plan["limits"]["reasons"][0])

    def test_reports_byte_budget_exceeded(self):
        plan = build_import_plan(
            self.candidate(), PREFIX, max_txn_ops=100, max_txn_bytes=1
        )
        self.assertFalse(plan["limits"]["fits"])
        self.assertTrue(any("bytes" in reason for reason in plan["limits"]["reasons"]))

    def test_rejects_scope_identity_that_could_restore_live_lease(self):
        candidate = self.candidate()
        scope = next(iter(candidate["state_template"]["coordinator"]["scopes"].values()))
        scope["lease_id"] = "legacy-live-lease"
        resign(candidate)
        with self.assertRaisesRegex(ImportPlanError, "live lease"):
            build_import_plan(candidate, PREFIX, max_txn_ops=100, max_txn_bytes=1_000_000)


if __name__ == "__main__":
    unittest.main()

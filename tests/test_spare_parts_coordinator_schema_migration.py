from __future__ import annotations

import copy
import unittest

from scripts.spare_parts_coordinator_schema_migration import (
    CoordinatorSchemaMigrationConflict,
    CoordinatorSchemaMigrationError,
    CoordinatorSchemaMigrationIntegrityError,
    CoordinatorSchemaMigrationModel,
    CoordinatorSchemaMigrationPolicyError,
    canonical_state_bytes,
)


SCOPE = "tenants/tenant-A/cnc/spares/pkg-001"


def v2_state():
    scope_row = {
        "high_water_token": 7,
        "lease_id": None,
        "owner_id": None,
        "tenant_id": None,
        "domain": None,
        "lease_expires_at": None,
        "lease_state": "REVOKED",
        "provider_generation": "provider-gen-7",
        "latest_operation_sequence": 12,
        "updated_at": 1_900_000_000.0,
    }
    operations = {
        "operation-key-1": {
            "scope": SCOPE,
            "kind": "PUBLISH",
            "idempotency_key": "publish-12",
            "request_sha256": "a" * 64,
            "fencing_token": 7,
            "operation_sequence": 12,
            "lease_id": "lease-7",
            "owner_id": "owner-A",
            "tenant_id": "tenant-A",
            "domain": "write",
            "lease_expires_at": 1_900_000_100.0,
            "state": "COMMITTED",
            "provider_generation": "provider-gen-7",
            "manifest_key": f"{SCOPE}/manifest-12.json",
            "manifest_sha256": "b" * 64,
            "created_at": 1_900_000_000.0,
            "updated_at": 1_900_000_001.0,
        }
    }
    return {
        "schema_version": 2,
        "policy_hash": "c" * 64,
        "global_limits": {"read": 4, "write": 2, "multipart": 2, "inventory": 1},
        "tenant_limits": {"tenant-A": {"write": 1}},
        "max_waiters": 256,
        "aging_interval_seconds": 1.0,
        "next_fencing_token": 7,
        "next_waiter_sequence": 4,
        "active": {},
        "waiters": [],
        "coordinator": {
            "leader": {"leader_id": "leader-A", "epoch": 9, "expires_at": 1_900_000_200.0},
            "scopes": {SCOPE: scope_row},
            "operations": operations,
        },
        "counters": {
            "issued_leases": 7,
            "expired_leases": 0,
            "released_leases": 7,
            "rejected_capacity": 0,
            "rejected_queue": 0,
        },
    }


def floors(state):
    return {
        scope: int(row["high_water_token"])
        for scope, row in state["coordinator"]["scopes"].items()
    }


def sequences(state):
    return {
        scope: int(row["latest_operation_sequence"])
        for scope, row in state["coordinator"]["scopes"].items()
    }


class CoordinatorSchemaMigrationTests(unittest.TestCase):
    def setUp(self):
        self.source = v2_state()
        self.model = CoordinatorSchemaMigrationModel(
            self.source,
            source_revision=42,
            leader_epoch=9,
        )

    def prepare_cutover(self):
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate()
        verified = self.model.verify_v3_candidate()
        self.assertTrue(verified["verified"])
        result = self.model.cutover(
            expected_source_revision=42,
            expected_leader_epoch=9,
            external_high_water_floors=floors(self.source),
            external_sequence_floors=sequences(self.source),
        )
        return result

    def test_v2_source_is_frozen_before_snapshot(self):
        result = self.model.begin_migration(expected_leader_epoch=9)
        self.assertTrue(result["writes_frozen"])
        self.assertEqual(result["source_revision"], 42)
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.mutate_v2("new-op", self.source["coordinator"]["operations"]["operation-key-1"])

    def test_stale_leader_epoch_cannot_begin_migration(self):
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.begin_migration(expected_leader_epoch=8)

    def test_candidate_is_split_into_versioned_logical_objects(self):
        self.model.begin_migration(expected_leader_epoch=9)
        result = self.model.build_v3_candidate()
        self.assertEqual(result["schema_version"], 3)
        self.assertIn("scheduler/core", self.model.v3_objects)
        self.assertIn("coordinator/scopes", self.model.v3_objects)
        self.assertIn("coordinator/hot-operations", self.model.v3_objects)
        self.assertEqual(result["operation_count"], 1)

    def test_candidate_preserves_verified_archive_index_pointers(self):
        pointer = {
            "scope": SCOPE,
            "index_generation": 2,
            "index_head_sha256": "a" * 64,
            "archive_generation": 2,
            "archive_head_sha256": "b" * 64,
            "operation_count": 15,
            "bucket_count": 256,
        }
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate(archive_index_pointers={SCOPE: pointer})
        report = self.model.verify_v3_candidate()
        self.assertTrue(report["verified"])
        import json
        value = json.loads(
            self.model.v3_objects["coordinator/archive-index-pointers"].decode("utf-8")
        )
        self.assertEqual(value[SCOPE], pointer)

    def test_candidate_rejects_malformed_archive_index_pointer(self):
        pointer = {
            "scope": SCOPE,
            "index_generation": 2,
            "index_head_sha256": "not-a-digest",
            "archive_generation": 2,
            "archive_head_sha256": "b" * 64,
            "operation_count": 15,
            "bucket_count": 256,
        }
        self.model.begin_migration(expected_leader_epoch=9)
        with self.assertRaises(CoordinatorSchemaMigrationPolicyError):
            self.model.build_v3_candidate(archive_index_pointers={SCOPE: pointer})

    def test_candidate_verification_checks_exact_source_representation(self):
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate()
        report = self.model.verify_v3_candidate()
        self.assertTrue(report["verified"])
        self.assertEqual(report["operation_count"], 1)

    def test_candidate_object_tampering_fails_verification(self):
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate()
        self.model.v3_objects["coordinator/hot-operations"] = b"{}"
        with self.assertRaises(CoordinatorSchemaMigrationIntegrityError):
            self.model.verify_v3_candidate()

    def test_candidate_cannot_cut_over_without_verification(self):
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate()
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.cutover(
                expected_source_revision=42,
                expected_leader_epoch=9,
                external_high_water_floors=floors(self.source),
                external_sequence_floors=sequences(self.source),
            )

    def test_source_revision_guard_blocks_stale_cutover(self):
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate()
        self.model.verify_v3_candidate()
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.cutover(
                expected_source_revision=41,
                expected_leader_epoch=9,
                external_high_water_floors=floors(self.source),
                external_sequence_floors=sequences(self.source),
            )

    def test_leader_epoch_guard_blocks_stale_cutover(self):
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate()
        self.model.verify_v3_candidate()
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.cutover(
                expected_source_revision=42,
                expected_leader_epoch=8,
                external_high_water_floors=floors(self.source),
                external_sequence_floors=sequences(self.source),
            )

    def test_external_fencing_floor_below_source_blocks_cutover(self):
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate()
        self.model.verify_v3_candidate()
        with self.assertRaises(CoordinatorSchemaMigrationPolicyError):
            self.model.cutover(
                expected_source_revision=42,
                expected_leader_epoch=9,
                external_high_water_floors={SCOPE: 6},
                external_sequence_floors=sequences(self.source),
            )

    def test_external_operation_sequence_below_source_blocks_cutover(self):
        self.model.begin_migration(expected_leader_epoch=9)
        self.model.build_v3_candidate()
        self.model.verify_v3_candidate()
        with self.assertRaises(CoordinatorSchemaMigrationPolicyError):
            self.model.cutover(
                expected_source_revision=42,
                expected_leader_epoch=9,
                external_high_water_floors=floors(self.source),
                external_sequence_floors={SCOPE: 11},
            )

    def test_cutover_keeps_writes_frozen_until_explicit_resume(self):
        result = self.prepare_cutover()
        self.assertEqual(result["active_schema"], 3)
        self.assertTrue(result["writes_frozen"])
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.record_v3_operation("new", {
                "scope": SCOPE, "fencing_token": 8, "operation_sequence": 13
            })

    def test_pre_write_pointer_rollback_is_allowed_while_frozen(self):
        self.prepare_cutover()
        result = self.model.rollback_before_v3_writes()
        self.assertEqual(result["active_schema"], 2)
        self.assertFalse(result["writes_frozen"])

    def test_pre_write_rollback_requires_frozen_gate(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.rollback_before_v3_writes()

    def test_stale_v2_pointer_rollback_is_forbidden_after_v3_write(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        self.model.record_v3_operation("operation-key-2", {
            "scope": SCOPE,
            "kind": "PUBLISH",
            "idempotency_key": "publish-13",
            "request_sha256": "d" * 64,
            "fencing_token": 8,
            "operation_sequence": 13,
            "state": "COMMITTED",
        })
        self.model.freeze_v3_for_reverse_migration()
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.rollback_before_v3_writes()

    def test_v3_rejects_lower_fencing_or_sequence_floor(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        with self.assertRaises(CoordinatorSchemaMigrationPolicyError):
            self.model.record_v3_operation("bad-token", {
                "scope": SCOPE, "fencing_token": 6, "operation_sequence": 13
            })
        with self.assertRaises(CoordinatorSchemaMigrationPolicyError):
            self.model.record_v3_operation("bad-sequence", {
                "scope": SCOPE, "fencing_token": 8, "operation_sequence": 11
            })

    def test_reverse_migration_requires_archive_lookup_complete(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        self.model.record_v3_operation("new-v3-op", {
            "scope": SCOPE,
            "kind": "PUBLISH",
            "idempotency_key": "new-v3-op",
            "request_sha256": "d" * 64,
            "fencing_token": 8,
            "operation_sequence": 13,
            "state": "COMMITTED",
        })
        self.model.freeze_v3_for_reverse_migration()
        shadow = copy.deepcopy(self.source)
        shadow["coordinator"]["operations"]["new-v3-op"] = {
            "scope": SCOPE,
            "kind": "PUBLISH",
            "idempotency_key": "new-v3-op",
            "request_sha256": "d" * 64,
            "fencing_token": 8,
            "operation_sequence": 13,
        }
        shadow["coordinator"]["scopes"][SCOPE]["high_water_token"] = 8
        shadow["coordinator"]["scopes"][SCOPE]["latest_operation_sequence"] = 13
        with self.assertRaises(CoordinatorSchemaMigrationIntegrityError):
            self.model.reverse_migrate_to_v2(
                shadow,
                archive_lookup_complete=False,
                external_high_water_floors={SCOPE: 8},
                external_sequence_floors={SCOPE: 13},
                max_v2_state_bytes=100_000,
            )

    def test_reverse_migration_requires_every_v3_accepted_operation(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        self.model.record_v3_operation("new-v3-op", {
            "scope": SCOPE, "fencing_token": 8, "operation_sequence": 13
        })
        self.model.freeze_v3_for_reverse_migration()
        with self.assertRaises(CoordinatorSchemaMigrationIntegrityError):
            self.model.reverse_migrate_to_v2(
                copy.deepcopy(self.source),
                archive_lookup_complete=True,
                external_high_water_floors={SCOPE: 8},
                external_sequence_floors={SCOPE: 13},
                max_v2_state_bytes=100_000,
            )

    def test_reverse_migration_preserves_v3_operations_and_high_water_floors(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        new_record = {
            "scope": SCOPE,
            "kind": "PUBLISH",
            "idempotency_key": "publish-13",
            "request_sha256": "d" * 64,
            "fencing_token": 8,
            "operation_sequence": 13,
            "state": "COMMITTED",
        }
        self.model.record_v3_operation("operation-key-2", new_record)
        self.model.freeze_v3_for_reverse_migration()
        shadow = copy.deepcopy(self.source)
        shadow["coordinator"]["operations"]["operation-key-2"] = new_record
        shadow["coordinator"]["scopes"][SCOPE]["high_water_token"] = 8
        shadow["coordinator"]["scopes"][SCOPE]["latest_operation_sequence"] = 13
        result = self.model.reverse_migrate_to_v2(
            shadow,
            archive_lookup_complete=True,
            external_high_water_floors={SCOPE: 8},
            external_sequence_floors={SCOPE: 13},
            max_v2_state_bytes=100_000,
        )
        self.assertEqual(result["rollback"], "REBUILT_FROM_V3_AND_ARCHIVE")
        self.assertEqual(self.model.v2_state["coordinator"]["scopes"][SCOPE]["high_water_token"], 8)
        self.assertIn("operation-key-2", self.model.v2_state["coordinator"]["operations"])

    def test_reverse_migration_rejects_lower_external_floor(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        self.model.record_v3_operation("new-v3-op", {
            "scope": SCOPE, "fencing_token": 8, "operation_sequence": 13
        })
        self.model.freeze_v3_for_reverse_migration()
        shadow = copy.deepcopy(self.source)
        shadow["coordinator"]["operations"]["new-v3-op"] = {
            "scope": SCOPE, "fencing_token": 8, "operation_sequence": 13
        }
        shadow["coordinator"]["scopes"][SCOPE]["high_water_token"] = 8
        shadow["coordinator"]["scopes"][SCOPE]["latest_operation_sequence"] = 13
        with self.assertRaises(CoordinatorSchemaMigrationPolicyError):
            self.model.reverse_migrate_to_v2(
                shadow,
                archive_lookup_complete=True,
                external_high_water_floors={SCOPE: 7},
                external_sequence_floors={SCOPE: 13},
                max_v2_state_bytes=100_000,
            )

    def test_reverse_migration_rejects_v2_size_overflow(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        self.model.freeze_v3_for_reverse_migration()
        with self.assertRaises(CoordinatorSchemaMigrationPolicyError):
            self.model.reverse_migrate_to_v2(
                copy.deepcopy(self.source),
                archive_lookup_complete=True,
                external_high_water_floors=floors(self.source),
                external_sequence_floors=sequences(self.source),
                max_v2_state_bytes=10,
            )

    def test_v3_writes_require_explicit_resume_and_can_be_frozen_again(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        self.model.freeze_v3_for_reverse_migration()
        self.assertTrue(self.model.writes_frozen)
        with self.assertRaises(CoordinatorSchemaMigrationConflict):
            self.model.record_v3_operation("blocked", {
                "scope": SCOPE, "fencing_token": 8, "operation_sequence": 13
            })

    def test_control_pointer_exposes_monotonic_control_epoch(self):
        self.prepare_cutover()
        before = self.model.control_pointer()["control_epoch"]
        self.model.rollback_before_v3_writes()
        after = self.model.control_pointer()["control_epoch"]
        self.assertGreater(after, before)

    def test_reverse_migration_rejects_invalid_size_limit(self):
        self.prepare_cutover()
        self.model.resume_v3_writes()
        self.model.freeze_v3_for_reverse_migration()
        with self.assertRaises(CoordinatorSchemaMigrationPolicyError):
            self.model.reverse_migrate_to_v2(
                copy.deepcopy(self.source),
                archive_lookup_complete=True,
                external_high_water_floors=floors(self.source),
                external_sequence_floors=sequences(self.source),
                max_v2_state_bytes=0,
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import unittest

from scripts.spare_parts_operation_ledger_archive import (
    InMemoryImmutableOperationArchiveStore,
    OperationArchiveCasConflictError,
    OperationArchiveConflictError,
    OperationArchiveIntegrityError,
    OperationArchiveOutcomeUnknownError,
    OperationArchivePolicyError,
    OperationArchiveUnavailableError,
    OperationLedgerArchiveModel,
    canonical_json_bytes,
    make_operation,
)


SCOPE_A = "tenants/tenant-A/cnc/spares/pkg-001"
SCOPE_B = "tenants/tenant-B/cnc/spares/pkg-002"
NOW = 1_900_000_000.0


def record(
    idem: str,
    *,
    scope: str = SCOPE_A,
    kind: str = "PUBLISH",
    state: str = "COMMITTED",
    token: int = 1,
    sequence: int | None = 1,
    updated_at: float = NOW - 10_000,
    digest_char: str = "a",
    lease_id: str = "lease-1",
):
    return make_operation(
        scope=scope,
        kind=kind,
        idempotency_key=idem,
        request_sha256=digest_char * 64,
        state=state,
        fencing_token=token,
        operation_sequence=sequence,
        lease_id=lease_id,
        manifest_key=f"{scope}/manifest-{idem}.json" if kind == "PUBLISH" else None,
        manifest_sha256=digest_char * 64 if kind == "PUBLISH" else None,
        provider_generation="provider-gen-1" if state in {"COMMITTED", "REVOKED", "ACTIVE"} else None,
        created_at=updated_at - 1,
        updated_at=updated_at,
    )


class OperationLedgerArchiveTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryImmutableOperationArchiveStore()
        self.model = OperationLedgerArchiveModel(self.store)
        self.model.create_scope(
            SCOPE_A,
            high_water_token=3,
            latest_operation_sequence=10,
            lease_state="REVOKED",
            lease_id="lease-3",
        )
        self.model.create_scope(
            SCOPE_B,
            high_water_token=1,
            latest_operation_sequence=2,
            lease_state="ACTIVE",
            lease_id="lease-B",
        )

    def archive(self, scope=SCOPE_A, **kwargs):
        options = {
            "now": NOW,
            "minimum_age_seconds": 0,
            "max_records": 100,
            "max_batch_bytes": 1_000_000,
        }
        options.update(kwargs)
        return self.model.archive_scope(scope, **options)

    def test_canonical_manifest_encoding_is_deterministic(self):
        first = {"b": 2, "a": 1}
        second = {"a": 1, "b": 2}
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_pending_operation_blocks_entire_scope_archive(self):
        self.model.insert_or_replay(record(
            "pending", state="PENDING_PUBLISH", sequence=11
        ))
        self.model.insert_or_replay(record("committed", sequence=10))
        result = self.archive()
        self.assertTrue(result["blocked"])
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 2)
        self.assertEqual(self.store.object_count, 0)

    def test_current_active_activation_is_not_eligible(self):
        self.model.snapshot(SCOPE_A)
        self.model.scopes[SCOPE_A]["lease_state"] = "ACTIVE"
        self.model.scopes[SCOPE_A]["lease_id"] = "lease-current"
        self.model.scopes[SCOPE_A]["high_water_token"] = 4
        self.model.insert_or_replay(record(
            "activate-current", kind="ACTIVATE", state="ACTIVE",
            token=4, sequence=None, lease_id="lease-current"
        ))
        result = self.archive()
        self.assertEqual(result["archived"], 0)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 1)

    def test_superseded_active_activation_can_be_archived(self):
        self.model.scopes[SCOPE_A]["lease_state"] = "ACTIVE"
        self.model.scopes[SCOPE_A]["lease_id"] = "lease-new"
        self.model.scopes[SCOPE_A]["high_water_token"] = 5
        self.model.insert_or_replay(record(
            "activate-old", kind="ACTIVATE", state="ACTIVE",
            token=4, sequence=None, lease_id="lease-old"
        ))
        result = self.archive()
        self.assertEqual(result["archived"], 1)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 0)
        self.assertEqual(self.model.lookup(SCOPE_A, "activate-old")["state"], "ACTIVE")

    def test_revoked_and_committed_terminal_operations_archive(self):
        self.model.insert_or_replay(record("published", sequence=10))
        self.model.insert_or_replay(record(
            "revoked", kind="REVOKE", state="REVOKED",
            sequence=None, token=3
        ))
        result = self.archive()
        self.assertEqual(result["archived"], 2)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 0)
        self.assertEqual(self.model.verify_scope_archive(SCOPE_A)["operation_count"], 2)

    def test_minimum_age_retains_recent_terminal_operations(self):
        self.model.insert_or_replay(record("recent", updated_at=NOW - 5))
        result = self.archive(minimum_age_seconds=60)
        self.assertEqual(result["archived"], 0)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 1)

    def test_batch_record_limit_bounds_archive_generation(self):
        for index in range(5):
            self.model.insert_or_replay(record(f"batch-{index}", sequence=index + 1))
        result = self.archive(max_records=2)
        self.assertEqual(result["archived"], 2)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 3)
        self.assertEqual(self.model.snapshot(SCOPE_A)["archive_generation"], 1)

    def test_batch_byte_limit_rejects_undersized_policy_without_mutation(self):
        self.model.insert_or_replay(record("large-record"))
        with self.assertRaises(OperationArchivePolicyError):
            self.archive(max_batch_bytes=20)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 1)
        self.assertEqual(self.model.snapshot(SCOPE_A)["archive_head_sha256"], None)

    def test_archived_idempotency_replay_returns_original_operation(self):
        original = record("replay-me", sequence=10)
        self.model.insert_or_replay(original)
        self.archive()
        replay = self.model.insert_or_replay(record(
            "replay-me", sequence=999, digest_char="a"
        ))
        self.assertEqual(replay["operation_sequence"], 10)
        self.assertEqual(self.model.snapshot(SCOPE_A)["latest_operation_sequence"], 10)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 0)

    def test_archived_idempotency_key_with_different_payload_is_rejected(self):
        self.model.insert_or_replay(record("conflict", digest_char="a"))
        self.archive()
        with self.assertRaises(OperationArchiveConflictError):
            self.model.insert_or_replay(record("conflict", digest_char="b"))

    def test_archive_read_unavailable_fails_closed_for_replay(self):
        self.model.insert_or_replay(record("archive-read"))
        self.archive()
        self.store.fail_next_read = True
        with self.assertRaises(OperationArchiveUnavailableError):
            self.model.insert_or_replay(record("archive-read"))

    def test_lost_immutable_put_response_is_reconciled_by_content_address(self):
        self.model.insert_or_replay(record("put-unknown"))
        self.store.lose_next_put_response = True
        result = self.archive()
        self.assertEqual(result["archived"], 1)
        self.assertEqual(self.model.lookup(SCOPE_A, "put-unknown")["state"], "COMMITTED")

    def test_lost_coordinator_commit_response_is_reconciled_by_authoritative_head(self):
        self.model.insert_or_replay(record("commit-unknown"))
        self.model.lose_next_commit_response = True
        result = self.archive()
        self.assertTrue(result["outcome_reconciled"])
        self.assertEqual(self.model.lookup(SCOPE_A, "commit-unknown")["state"], "COMMITTED")

    def test_unknown_coordinator_commit_response_never_rolls_back_archive(self):
        self.model.insert_or_replay(record("commit-unknown-unreadable"))
        self.model.lose_next_commit_response = True
        original_read = self.model.scope_read_available
        self.model.scope_read_available = False
        with self.assertRaises(OperationArchiveOutcomeUnknownError):
            self.archive()
        self.model.scope_read_available = original_read
        self.assertEqual(self.model.snapshot(SCOPE_A)["archive_operation_count"], 1)
        self.assertEqual(self.model.lookup(SCOPE_A, "commit-unknown-unreadable")["state"], "COMMITTED")

    def test_cas_conflict_keeps_hot_records_and_leaves_only_orphan_object(self):
        self.model.insert_or_replay(record("cas-old"))
        def concurrent_change(model):
            model.insert_or_replay(record("cas-new", sequence=11))
        with self.assertRaises(OperationArchiveCasConflictError):
            self.archive(before_commit=concurrent_change)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 2)
        self.assertIsNone(self.model.snapshot(SCOPE_A)["archive_head_sha256"])
        self.assertEqual(self.store.object_count, 1)

    def test_manifest_chain_verifies_across_multiple_archive_batches(self):
        self.model.insert_or_replay(record("first", sequence=10))
        first = self.archive()
        self.model.insert_or_replay(record("second", sequence=11))
        second = self.archive()
        self.assertNotEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(self.model.snapshot(SCOPE_A)["archive_generation"], 2)
        verified = self.model.verify_scope_archive(SCOPE_A)
        self.assertEqual(verified["batch_count"], 2)
        self.assertEqual(verified["operation_count"], 2)

    def test_corrupt_archive_object_fails_closed(self):
        self.model.insert_or_replay(record("tamper"))
        result = self.archive()
        self.store.corrupt_for_test(result["manifest_sha256"], b"{}")
        with self.assertRaises(OperationArchiveIntegrityError):
            self.model.lookup(SCOPE_A, "tamper")

    def test_archive_chain_scope_isolation(self):
        self.model.insert_or_replay(record("tenant-a"))
        self.model.insert_or_replay(record("tenant-b", scope=SCOPE_B, sequence=2))
        self.archive(SCOPE_A)
        self.assertEqual(self.model.lookup(SCOPE_A, "tenant-a")["scope"], SCOPE_A)
        self.assertEqual(self.model.lookup(SCOPE_B, "tenant-b")["scope"], SCOPE_B)
        self.assertEqual(self.model.snapshot(SCOPE_B)["archive_generation"], 0)

    def test_high_water_token_and_publish_sequence_are_not_reduced(self):
        self.model.insert_or_replay(record("keep-floors", token=5, sequence=12))
        before = self.model.snapshot(SCOPE_A)
        self.archive()
        after = self.model.snapshot(SCOPE_A)
        self.assertEqual(after["high_water_token"], before["high_water_token"])
        self.assertEqual(
            after["latest_operation_sequence"],
            before["latest_operation_sequence"],
        )

    def test_archive_store_write_failure_leaves_hot_authority_unchanged(self):
        self.model.insert_or_replay(record("put-fail"))
        self.store.fail_next_put = True
        with self.assertRaises(OperationArchiveUnavailableError):
            self.archive()
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 1)
        self.assertIsNone(self.model.snapshot(SCOPE_A)["archive_head_sha256"])

    def test_archive_store_readback_failure_leaves_hot_authority_unchanged(self):
        self.model.insert_or_replay(record("readback-fail"))
        # First read is the archive verification read-back after a successful put.
        self.store.fail_next_read = True
        with self.assertRaises(OperationArchiveUnavailableError):
            self.archive()
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 1)
        self.assertIsNone(self.model.snapshot(SCOPE_A)["archive_head_sha256"])

    def test_archive_objects_are_not_physically_deleted_by_protocol(self):
        self.model.insert_or_replay(record("no-delete"))
        result = self.archive()
        with self.assertRaises(OperationArchivePolicyError):
            self.model.physical_delete_archive_object(result["manifest_sha256"])
        self.assertEqual(self.store.object_count, 1)

    def test_archive_policy_rejects_invalid_batch_limits(self):
        self.model.insert_or_replay(record("invalid-policy"))
        with self.assertRaises(OperationArchivePolicyError):
            self.archive(max_records=0)
        with self.assertRaises(OperationArchivePolicyError):
            self.archive(max_batch_bytes=0)
        with self.assertRaises(OperationArchivePolicyError):
            self.archive(minimum_age_seconds=-1)
        self.assertEqual(self.model.hot_operation_count(SCOPE_A), 1)

    def test_archive_index_identity_is_bound_to_full_operation_digest(self):
        self.model.insert_or_replay(record("identity"))
        self.archive()
        found = self.model.lookup(SCOPE_A, "identity")
        self.assertEqual(found["request_sha256"], "a" * 64)
        self.assertEqual(found["kind"], "PUBLISH")
        self.assertEqual(found["idempotency_key"], "identity")


if __name__ == "__main__":
    unittest.main()
